"""
Citation Engine

Enterprise Compliance Intelligence Platform

Purpose
-------
Convert pre-computed GraphRAG retrieval context into citable evidence.

Receives retrieval context already produced by GraphRAGQuery —
never performs similarity search itself.

Future Version
--------------
Will support:
- Exact PDF page numbers
- Bounding boxes
- Image references
- Table references
- Audio timestamps
"""



class CitationEngine:

    def build_citations(
        self,
        retrieval_context: dict,
        graph,
        text_chunks: dict,
    ) -> list[dict]:
        """
        Build citations from pre-computed retrieval context.

        Parameters
        ----------
        retrieval_context : dict
            The ``"retrieval"`` sub-dict from
            ``GraphRAGQuery.query(return_context=True)``.
        graph : networkx.Graph
            Loaded knowledge graph (``query_engine.graph``).
        text_chunks : dict
            KV store of text chunks (``query_engine.text_chunks``).

        Returns
        -------
        List[dict]  — deduplicated by source_chunk
        """

        similar_nodes: list[tuple[str, float]] = retrieval_context.get(
            "similar_nodes", []
        )

        citations = []

        for node_name, similarity in similar_nodes:

            if node_name not in graph:
                continue

            node = graph.nodes[node_name]

            description = node.get("description", "")
            entity_type = node.get("entity_type", "UNKNOWN").replace('"', "")

            for raw_sid in node.get("source_id", "").split("<SEP>"):
                sid = raw_sid.strip()
                if not sid:
                    continue
                chunk = text_chunks.get(sid)
                if chunk is None:
                    continue
                citations.append({
                    "entity":      node_name,
                    "entity_type": entity_type,
                    "confidence":  round(similarity, 3),
                    "source_chunk": sid,
                    "excerpt":     chunk.get("content", "")[:350],
                    "description": description,
                })

        # Deduplicate by source_chunk. Similar nodes are score-descending, so
        # preserve the first (highest-confidence) entity for each source.
        unique: dict[str, dict] = {}
        for citation in citations:
            unique.setdefault(citation["source_chunk"], citation)

        return list(unique.values())
