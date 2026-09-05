"""
Graph API — CLI / legacy use only.

This module is NOT registered in main.py. All authenticated graph requests
are handled by workspace_graph.py at /api/graph, which is workspace-scoped.

This file is kept for local CLI inspection of the global output directory.
Do NOT import `settings` (a QueryParam class) — use flat config vars instead.
"""

import networkx as nx
from fastapi import APIRouter, HTTPException

from backend.config.settings import MMKG_NAME, OUTPUT_DIR

router = APIRouter(
    prefix="/graph",
    tags=["Knowledge Graph"]
)


def _load_graph():
    graph_path = f"{OUTPUT_DIR}/{MMKG_NAME}.graphml"

    try:
        return nx.read_graphml(graph_path)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail="Knowledge graph not found.",
        ) from exc


@router.get("/summary")
async def graph_summary():

    graph = _load_graph()

    entity_types = {}

    for _, node in graph.nodes(data=True):

        entity = (
            node.get(
                "entity_type",
                "UNKNOWN"
            )
            .replace('"', "")
        )

        entity_types[entity] = (
            entity_types.get(entity, 0) + 1
        )

    return {

        "nodes": graph.number_of_nodes(),

        "edges": graph.number_of_edges(),

        "entity_types": entity_types

    }


@router.get("/entities")
async def entities(limit: int = 100):

    graph = _load_graph()

    response = []

    for node_name, node in list(graph.nodes(data=True))[:limit]:

        response.append({

            "name": node_name,

            "type": node.get(
                "entity_type",
                "UNKNOWN"
            ),

            "description": node.get(
                "description",
                ""
            )

        })

    return response


@router.get("/relationships")
async def relationships(limit: int = 100):

    graph = _load_graph()

    response = []

    for source, target, edge in list(
        graph.edges(data=True)
    )[:limit]:

        response.append({

            "source": source,

            "target": target,

            "description": edge.get(
                "description",
                ""
            ),

            "weight": edge.get(
                "weight",
                1
            )

        })

    return response


@router.get("/network")
async def graph_network():
    """Serialize the loaded graph into a frontend-friendly network payload."""
    graph = _load_graph()

    nodes = [
        {
            "id": str(node_id),
            "label": str(node_data.get("label") or node_id),
            "type": str(node_data.get("entity_type") or node_data.get("type") or "UNKNOWN"),
            "description": str(node_data.get("description") or ""),
        }
        for node_id, node_data in graph.nodes(data=True)
    ]

    edges = [
        {
            "id": f"{source}->{target}",
            "source": str(source),
            "target": str(target),
            "weight": edge_data.get("weight", 1),
            "description": str(edge_data.get("description") or ""),
        }
        for source, target, edge_data in graph.edges(data=True)
    ]

    return {"nodes": nodes, "edges": edges}
