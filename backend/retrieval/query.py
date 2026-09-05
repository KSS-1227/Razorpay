"""
GraphRAG query engine — semantic retrieval over the knowledge graph.
"""
import asyncio
import base64
import os

import networkx as nx
import numpy as np

from ..config import settings as parameter
from ..core.prompt import PROMPTS
from ..llm import model_if_cache, multimodel_if_cache
from ..storage.kv_storage import JsonKVStorage
from ..utils.base import (
    get_latest_graphml_file,
    list_of_list_to_csv,
    load_json,
    logger,
    truncate_list_by_token_size,
)
from .. import cockroach_vector_storage as vector_store


class GraphRAGQuery:
    def __init__(self, graph_path=None, embedding_path=None, working_dir=None,
                 cache_path=None, workspace_id=None):
        self.working_dir    = working_dir or parameter.WORKING_DIR
        self.cache_path     = cache_path or parameter.CACHE_PATH  # T4: accept per-workspace cache path
        self.workspace_id   = workspace_id  # NEW — required for the CockroachDB vector index

        _namespace, default_graph_path = get_latest_graphml_file(self.working_dir)
        self.graph_path     = graph_path or default_graph_path
        self.embedding_path = embedding_path or os.path.join(
            parameter.OUTPUT_DIR, f"{parameter.MMKG_NAME}_emb.npy"
        )

        if not os.path.exists(self.graph_path):
            raise FileNotFoundError(
                "Knowledge graph snapshot not found. Upload and index a document first. "
                f"(Expected: {self.graph_path})"
            )
        self.embed_model    = parameter.get_embed_model()
        self.graph          = nx.read_graphml(self.graph_path)
        self.node_list      = list(self.graph.nodes())
        self.llm_cache      = JsonKVStorage(namespace="llm_response_cache",    storage_dir=self.cache_path)
        self.mm_cache       = JsonKVStorage(namespace="multimodel_llm_response_cache", storage_dir=self.cache_path)
        self.text_chunks    = load_json(os.path.join(self.working_dir, "kv_store_text_chunks.json")) or {}
        self.image_data     = load_json(os.path.join(self.working_dir, "kv_store_image_data.json")) or {}

        # Embeddings now live in CockroachDB's entity_embeddings table, kept
        # in sync by MMKGBuilder._step_embeddings() after extraction — see
        # builder.py. Nothing to load here anymore; find_similar_nodes()
        # below queries the vector index directly, on demand, per question.
        if not self.workspace_id:
            raise ValueError("GraphRAGQuery requires workspace_id to query the vector index")

    async def find_similar_nodes(self, query: str, top_k: int = 5):
        q_emb = self.embed_model.encode([query])[0]
        return await vector_store.top_k_similar(self.workspace_id, q_emb, k=top_k)

    def _find_most_related_text_unit_from_entities(self, node_datas):
        text_units = []
        for node in node_datas:
            source_ids = node.get("source_id", "")
            for raw_sid in source_ids.split("<SEP>"):
                sid = raw_sid.strip()
                if sid in self.text_chunks:
                    text_units.append(self.text_chunks[sid])
        return text_units

    def _find_most_related_edges_from_entities(self, node_datas):
        edges = []
        for node in node_datas:
            name = node.get("entity_name", "")
            if name in self.graph:
                for _src, _tgt, data in self.graph.edges(name, data=True):
                    edges.append(data)
        return edges

    async def _build_local_query_context(self, query, top_k=5):
        # --- single similarity search for this entire request ---
        similar_nodes = await self.find_similar_nodes(query, top_k=top_k)

        node_datas = []
        for node_name, score in similar_nodes:
            if score < parameter.RETRIEVAL_THRESHOLD:
                continue
            node_data = dict(self.graph.nodes[node_name])
            node_data["entity_name"] = node_name
            node_datas.append(node_data)

        entities_context = list_of_list_to_csv([
            ["entity_name", "entity_type", "description"]
        ] + [
            [n.get("entity_name", ""), n.get("entity_type", ""), n.get("description", "")]
            for n in node_datas
        ])

        text_units = self._find_most_related_text_unit_from_entities(node_datas)
        text_units = truncate_list_by_token_size(
            text_units, key=lambda x: x.get("content", ""),
            max_token_size=parameter.QueryParam.local_max_token_for_text_unit
        )
        sources_context = "\n".join(t.get("content", "") for t in text_units)

        edges = self._find_most_related_edges_from_entities(node_datas)
        rels_context = list_of_list_to_csv([
            ["description", "weight"]
        ] + [
            [e.get("description", ""), str(e.get("weight", ""))] for e in edges
        ])

        # Return similar_nodes alongside context so query() can surface it
        # to callers without a second embedding call.
        return entities_context, sources_context, rels_context, node_datas, similar_nodes

    async def query(self, question: str, param=None, return_context: bool = False):
        """
        Execute the full GraphRAG query pipeline.

        Parameters
        ----------
        question : str
            Natural language question.
        param : QueryParam, optional
            Retrieval configuration. Defaults to settings.QueryParam.
        return_context : bool, default False
            When False (default) returns the answer string only — fully
            backward compatible with all existing callers (CLI, Flask viz).
            When True returns a structured dict so upstream services can
            consume pre-computed retrieval context without a second
            embedding call::

                {
                    "answer": "...",
                    "retrieval": {
                        "similar_nodes":         [(name, score), ...],
                        "node_datas":            [...],
                        "entities_context":      "...",
                        "sources_context":       "...",
                        "relationships_context": "...",
                    }
                }
        """
        if param is None:
            param = parameter.QueryParam

        # Single retrieval call — similar_nodes is now returned by
        # _build_local_query_context alongside the LLM context strings.
        entities_ctx, sources_ctx, rels_ctx, node_datas, similar_nodes = (
            await self._build_local_query_context(question, top_k=param.top_k)
        )

        # ----------------------------------------------------------------
        # Stage 1 — text-only GraphRAG answer
        # ----------------------------------------------------------------
        # Build a combined context_data string from entities, relationships, sources
        context_data = (
            f"## Entities\n{entities_ctx}\n\n"
            f"## Relationships\n{rels_ctx}\n\n"
            f"## Source Text\n{sources_ctx}"
        )
        sys_prompt = PROMPTS["local_rag_response_augmented"].format(
            response_type=param.response_type,
            context_data=context_data,
        )
        user_prompt = f"Question: {question}"
        text_answer = await model_if_cache(
            user_prompt, system_prompt=sys_prompt, hashing_kv=self.llm_cache
        )

        # ----------------------------------------------------------------
        # Stage 2 — multimodal augmentation
        # ----------------------------------------------------------------
        mm_entities = [
            n for n in node_datas
            if n.get("entity_type", "").strip('"').upper() in ["ORI_IMG", "IMG"]
        ][:param.number_of_mmentities]

        if not mm_entities:
            await self.llm_cache.index_done_callback()
            final_answer = text_answer
        else:
            mm_answers = []
            for node in mm_entities:
                name = node.get("entity_name", "").strip('"')
                img_info = self.image_data.get(name) or self.image_data.get(f'"{name}"')
                if not img_info:
                    continue
                img_path = img_info.get("image_path", "")
                if not os.path.exists(img_path):
                    continue
                with open(img_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode("utf-8")
                mm_sys = PROMPTS["local_rag_response_multimodal"].format(
                    response_type=param.response_type,
                    context_data=context_data,
                    image_information=node.get("description", ""),
                )
                mm_ans = await multimodel_if_cache(
                    user_prompt=f"Question: {question}",
                    img_base=img_b64,
                    system_prompt=mm_sys,
                    hashing_kv=self.mm_cache,
                )
                mm_answers.append(mm_ans)

            if not mm_answers:
                await self.llm_cache.index_done_callback()
                final_answer = text_answer
            else:
                # Stage 3 — merge text + multimodal answers
                merge_prompt = PROMPTS["local_rag_response_merge"].format(
                    response_type=param.response_type,
                    mm_response="\n---\n".join(mm_answers),
                    response=text_answer,
                )
                final_answer = await model_if_cache(
                    merge_prompt,
                    system_prompt=f"You are a helpful assistant. Respond in: {param.response_type}",
                    hashing_kv=self.llm_cache,
                )
                await asyncio.gather(
                    self.llm_cache.index_done_callback(),
                    self.mm_cache.index_done_callback(),
                )

        # ----------------------------------------------------------------
        # Return — backward-compatible by default
        # ----------------------------------------------------------------
        if not return_context:
            return final_answer

        return {
            "answer": final_answer,
            "retrieval": {
                "similar_nodes":         similar_nodes,
                "node_datas":            node_datas,
                "entities_context":      entities_ctx,
                "sources_context":       sources_ctx,
                "relationships_context": rels_ctx,
            },
        }
