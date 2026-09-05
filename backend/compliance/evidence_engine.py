"""
Evidence Engine

Enterprise Compliance Intelligence Platform

Purpose
-------
Provide explainable evidence for every GraphRAG response.

Responsibilities
----------------
- Collect supporting entities
- Collect supporting relationships
- Collect supporting document chunks
- Collect supporting images
- Build an explainable evidence package

This module NEVER generates answers.
It NEVER performs retrieval or similarity search.
It only explains WHY the answer was produced,
using retrieval context already computed by GraphRAGQuery.
"""



class EvidenceEngine:

    def collect(
        self,
        retrieval_context: dict,
        graph,
        text_chunks: dict,
        image_data: dict,
    ) -> dict:
        """
        Build an evidence package from pre-computed retrieval context.

        Parameters
        ----------
        retrieval_context : dict
            The ``"retrieval"`` sub-dict returned by
            ``GraphRAGQuery.query(return_context=True)``.  Expected keys:

            - ``similar_nodes``   : List[Tuple[str, float]]
            - ``node_datas``      : List[dict]   (threshold-filtered)
            - ``entities_context``, ``sources_context``,
              ``relationships_context`` : str  (already formatted for LLM)

        graph : networkx.Graph
            The loaded knowledge graph (``query_engine.graph``).
        text_chunks : dict
            KV store of text chunks (``query_engine.text_chunks``).
        image_data : dict
            KV store of image metadata (``query_engine.image_data``).

        Returns
        -------
        dict
            ``{"entities": [...], "relationships": [...],
               "text_chunks": [...], "images": [...]}``
        """

        similar_nodes: list[tuple[str, float]] = retrieval_context.get(
            "similar_nodes", []
        )

        evidence = {
            "entities":      [],
            "relationships": [],
            "text_chunks":   [],
            "images":        [],
        }

        visited_chunks: set = set()

        # -------------------------------------------------------
        # Supporting Entities + Text Chunks
        # -------------------------------------------------------

        for entity_name, similarity in similar_nodes:

            if entity_name not in graph:
                continue

            node = graph.nodes[entity_name]

            source_ids = [
                s.strip()
                for s in node.get("source_id", "").split("<SEP>")
                if s.strip()
            ]
            source_files = sorted(set(
                text_chunks[sid].get("file_name", "unknown")
                for sid in source_ids
                if sid in text_chunks
            ))

            evidence["entities"].append({
                "name":         entity_name,
                "type":         node.get("entity_type", "UNKNOWN").replace('"', ""),
                "confidence":   round(similarity, 3),
                "description":  node.get("description", ""),
                "source_files": source_files,
            })

            for raw_sid in node.get("source_id", "").split("<SEP>"):
                sid = raw_sid.strip()
                if not sid or sid in visited_chunks:
                    continue
                visited_chunks.add(sid)
                chunk = text_chunks.get(sid)
                if chunk is None:
                    continue
                content = chunk.get("content", "")
                evidence["text_chunks"].append({
                    "chunk_id":    sid,
                    "text":        content,
                    "tokens":      len(content.split()),
                    "source_file": chunk.get("file_name", "unknown"),
                })

        # -------------------------------------------------------
        # Supporting Relationships
        # -------------------------------------------------------

        added: set = set()

        for entity_name, _ in similar_nodes:

            if entity_name not in graph:
                continue

            for source, target, edge in graph.edges(entity_name, data=True):
                key = (source, target)
                if key in added:
                    continue
                added.add(key)
                evidence["relationships"].append({
                    "source":      source,
                    "target":      target,
                    "description": edge.get("description", ""),
                    "weight":      edge.get("weight", 1.0),
                })

        # -------------------------------------------------------
        # Supporting Images
        # -------------------------------------------------------

        for entity_name, _ in similar_nodes:
            image = image_data.get(entity_name)
            if image:
                evidence["images"].append({
                    "entity":     entity_name,
                    "image_path": image.get("image_path", ""),
                })

        return evidence