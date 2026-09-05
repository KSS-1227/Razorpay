"""
Text-to-graph pipeline: extracts entities and relations from text chunks.
"""
import asyncio
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import cast

from tqdm import tqdm

from ..config import settings as parameter
from ..cockroach_graph_storage import CockroachGraphStorage
from ..core.prompt import PROMPTS
from ..llm import model_if_cache
from ..storage.graph_storage import BaseGraphStorage
from ..storage.kv_storage import (
    BaseKVStorage,
    JsonKVStorage,
    StorageNameSpace,
    TextChunkSchema,
)
from ..utils.base import (
    limit_async_func_call,
    logger,
    pack_user_ass_to_openai_messages,
    split_string_by_multi_markers,
)
from .utils import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction,
    _merge_edges_then_upsert,
    _merge_nodes_then_upsert,
)

TUPLE_DELIMITER      = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
RECORD_DELIMITER     = PROMPTS["DEFAULT_RECORD_DELIMITER"]
COMPLETION_DELIMITER = PROMPTS["DEFAULT_COMPLETION_DELIMITER"]
PROCESS_TICKERS      = PROMPTS["process_tickers"]


async def extract_entities(
    cache_storage: BaseKVStorage,
    chunks: dict[str, TextChunkSchema],
    knwoledge_graph_inst: BaseGraphStorage,
    working_dir: str = None,
) -> BaseGraphStorage | None:
    output_path = os.path.join(working_dir or parameter.WORKING_DIR, "kv_store_chunk_knowledge_graph.json")

    llm_func = limit_async_func_call(16)(
        partial(model_if_cache, hashing_kv=cache_storage)
    )

    max_gleaning   = parameter.ENTITY_EXTRACT_MAX_GLEANING
    ordered_chunks = list(chunks.items())

    entity_prompt    = PROMPTS["entity_extraction"]
    continue_prompt  = PROMPTS["entity_continue_extraction"]
    loop_prompt      = PROMPTS["entity_if_loop_extraction"]

    context = {
        "tuple_delimiter":      TUPLE_DELIMITER,
        "record_delimiter":     RECORD_DELIMITER,
        "completion_delimiter": COMPLETION_DELIMITER,
        "entity_types":         ",".join(PROMPTS["DEFAULT_ENTITY_TYPES"]),
    }

    chunk_kg_info = {}

    async def process_chunk(chunk_item):
        chunk_key, chunk_data = chunk_item
        content     = chunk_data["content"]
        chunk_index = chunk_data["chunk_order_index"]

        prompt  = entity_prompt.format(**context, input_text=content)
        result  = await llm_func(prompt)
        history = pack_user_ass_to_openai_messages(prompt, result)

        for i in range(max_gleaning):
            glean_result = await llm_func(continue_prompt, history_messages=history)
            history += pack_user_ass_to_openai_messages(continue_prompt, glean_result)
            result  += glean_result
            if i < max_gleaning - 1:
                should_continue = await llm_func(loop_prompt, history_messages=history)
                if should_continue.strip().strip("'\"").lower() != "yes":
                    break

        records = split_string_by_multi_markers(result, [RECORD_DELIMITER, COMPLETION_DELIMITER])

        nodes        = defaultdict(list)
        edges        = defaultdict(list)
        chunk_result = {"chunk_key": chunk_key, "entities": [], "relationships": []}

        for record in records:
            match = re.search(r"\((.*)\)", record)
            if not match:
                continue
            attrs = split_string_by_multi_markers(match.group(1), [TUPLE_DELIMITER])
            entity = await _handle_single_entity_extraction(attrs, chunk_key)
            if entity:
                nodes[entity["entity_name"]].append(entity)
                chunk_result["entities"].append(entity)
                continue
            relation = await _handle_single_relationship_extraction(attrs, chunk_key)
            if relation:
                edges[(relation["src_id"], relation["tgt_id"])].append(relation)
                chunk_result["relationships"].append(relation)

        chunk_kg_info[chunk_index] = chunk_result
        return dict(nodes), dict(edges)

    tasks = [process_chunk(chunk) for chunk in ordered_chunks]
    results = [
        await coro
        for coro in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="📝 Text entity extraction",
            unit="chunk",
        )
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunk_kg_info, f, ensure_ascii=False, indent=2)

    all_nodes = defaultdict(list)
    all_edges = defaultdict(list)
    for nodes, edges in results:
        for k, v in nodes.items():
            all_nodes[k].extend(v)
        for k, v in edges.items():
            all_edges[tuple(sorted(k))].extend(v)

    entities_data = await asyncio.gather(*[
        _merge_nodes_then_upsert(k, v, knwoledge_graph_inst) for k, v in all_nodes.items()
    ])
    await asyncio.gather(*[
        _merge_edges_then_upsert(k[0], k[1], v, knwoledge_graph_inst) for k, v in all_edges.items()
    ])

    if not entities_data:
        logger.warning("No entities extracted")
        return None
    return knwoledge_graph_inst


@dataclass
class TextEntityExtractor:
    extraction_func:   callable              = extract_entities
    kv_storage_cls:    type[BaseKVStorage]   = JsonKVStorage
    graph_storage_cls: type[BaseGraphStorage] = CockroachGraphStorage
    working_dir:       str                   = None
    cache_dir:         str                   = None
    workspace_id:      str | None            = None

    def __post_init__(self):
        if not self.workspace_id:
            raise ValueError(
                "TextEntityExtractor requires workspace_id when using "
                "CockroachGraphStorage"
            )
        self.llm_cache = self.kv_storage_cls(
            namespace="llm_response_cache",
            storage_dir=self.cache_dir or parameter.CACHE_PATH
        )
        self.graph = self.graph_storage_cls(
            namespace="chunk_entity_relation",
            workspace_id=self.workspace_id,
            storage_dir=self.working_dir,
        )

    async def text_entity_extraction(self, chunks: dict):
        try:
            logger.info("🔍 Extracting entities...")
            result = await self.extraction_func(
                self.llm_cache, chunks, knwoledge_graph_inst=self.graph,
                working_dir=self.working_dir,
            )
            if result is None:
                logger.warning("No new entities found")
            else:
                self.graph = result
        finally:
            await self._save()

    async def _save(self):
        tasks = [
            cast(StorageNameSpace, s).index_done_callback()
            for s in [self.llm_cache, self.graph] if s
        ]
        await asyncio.gather(*tasks)
