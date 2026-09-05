"""
Compliance Report API

Generates a structured compliance report from the
current Knowledge Graph and GraphRAG response.

Future:
- PDF Export
- DOCX Export
- HTML Report
"""

from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.services.query_service import QueryService

router = APIRouter(
    prefix="/report",
    tags=["Compliance Report"]
)


class ReportRequest(BaseModel):
    question: str
    top_k: int = 10


@router.post("/")
async def generate_report(request: ReportRequest):

    graph_path = (
        Path(settings.OUTPUT_DIR)
        / f"{settings.MMKG_NAME}.graphml"
    )

    if not graph_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Knowledge Graph not found."
        )

    graph = nx.read_graphml(graph_path)

    service = QueryService()

    result = await service.ask(
        request.question,
        request.top_k
    )

    entity_distribution = {}

    for _, data in graph.nodes(data=True):

        entity = (
            data.get(
                "entity_type",
                "UNKNOWN"
            )
            .replace('"', "")
        )

        entity_distribution[entity] = (
            entity_distribution.get(entity, 0) + 1
        )

    report = {

        "generated_at": datetime.now(tz=UTC).isoformat(),

        "knowledge_graph": {

            "nodes": graph.number_of_nodes(),

            "edges": graph.number_of_edges(),

            "entity_distribution": entity_distribution

        },

        "query": request.question,

        "answer": result["answer"],

        "evidence": result.get(
            "evidence",
            {}
        ),

        "retrieved_entities": result.get(
            "retrieved_entities",
            []
        ),

        "prototype": {

            "engine": "MMGraphRAG",

            "multimodal": True,

            "retrieval": "GraphRAG"

        }

    }

    return {

        "success": True,

        "report": report

    }
