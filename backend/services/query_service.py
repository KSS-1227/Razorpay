"""
Query Service

Wrapper around MMGraphRAG GraphRAGQuery.

Responsibilities
----------------
1. Validate graph availability
2. Execute GraphRAG query (single retrieval call via return_context=True)
3. Pass pre-computed retrieval context to EvidenceEngine
4. Return clean structured response — answer + evidence
"""

import time
from pathlib import Path

from backend.compliance.evidence_engine import EvidenceEngine
from backend.config import settings
from backend.retrieval.query import GraphRAGQuery
from backend.utils.base import get_latest_graphml_file


class QueryService:

    async def ask(self, case_id: str, question: str, top_k: int = 10) -> dict:
        _, resolved_graph = get_latest_graphml_file(settings.WORKING_DIR)
        if not Path(resolved_graph).exists():
            raise FileNotFoundError(
                "Knowledge Graph not found. Upload and process a document first."
            )

        start = time.time()

        query_engine = GraphRAGQuery(workspace_id=case_id)

        # Override retrieval size dynamically
        settings.QueryParam.top_k = top_k

        # Single call — retrieval happens exactly once inside query().
        # return_context=True surfaces the already-computed similar_nodes
        # and context strings; no second embedding call is made.
        result = await query_engine.query(question, return_context=True)

        answer           = result["answer"]
        retrieval_context = result["retrieval"]

        processing_time = round(time.time() - start, 2)

        # EvidenceEngine receives the pre-computed retrieval context and
        # the raw data stores — it performs zero similarity search itself.
        evidence = EvidenceEngine().collect(
            retrieval_context=retrieval_context,
            graph=query_engine.graph,
            text_chunks=query_engine.text_chunks,
            image_data=query_engine.image_data,
        )

        return {
            "answer": answer,
            "evidence": evidence,
            "processing_time_seconds": processing_time,
            "graph": {
                "nodes": query_engine.graph.number_of_nodes(),
                "edges": query_engine.graph.number_of_edges(),
            },
        }
