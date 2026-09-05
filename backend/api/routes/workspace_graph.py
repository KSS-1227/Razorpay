"""
Workspace-aware graph route.

Replaces graph.py for authenticated requests.
Graph files are read from:
    data/users/{user_id}/cases/{case_id}/output/graph.graphml

The original graph.py is NOT modified.
"""
from __future__ import annotations

import hashlib

import networkx as nx
from fastapi import APIRouter, Depends, HTTPException

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.services.case_service import get_case as _verify_case_ownership
from backend.auth.workspace import UserWorkspace

router = APIRouter(
    prefix="/graph",
    tags=["Knowledge Graph"],
)


def _load_graph(ws: UserWorkspace) -> nx.Graph:
    """Load the graph from the user's workspace output directory."""
    # Try workspace graph.graphml first, then MMKG_NAME fallback
    from backend.config import MMKG_NAME
    candidates = [
        ws.graph_path,
        ws.output / f"{MMKG_NAME}.graphml",
    ]
    for path in candidates:
        if path.exists():
            try:
                return nx.read_graphml(str(path))
            except Exception as exc:
                raise HTTPException(
                    status_code=500, detail=f"Could not read graph: {exc}"
                ) from exc
    raise HTTPException(
        status_code=404,
        detail="Knowledge graph not found for this case. Upload and process documents first.",
    )


@router.get("/summary")
async def graph_summary(
    case_id: str,
    auth: AuthContext = Depends(get_current_user),
):
    """Return node/edge/entity-type summary for a case's knowledge graph."""
    await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)
    ws    = UserWorkspace(user_id=auth.user_id, case_id=case_id)
    graph = _load_graph(ws)

    entity_types: dict = {}
    for _, node in graph.nodes(data=True):
        etype = node.get("entity_type", "UNKNOWN").replace('"', "")
        entity_types[etype] = entity_types.get(etype, 0) + 1

    return {
        "case_id":      case_id,
        "nodes":        graph.number_of_nodes(),
        "edges":        graph.number_of_edges(),
        "entity_types": entity_types,
    }


@router.get("/entities")
async def entities(
    case_id: str,
    limit: int = 100,
    auth: AuthContext = Depends(get_current_user),
):
    """Return entities from a case's knowledge graph."""
    await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)
    ws    = UserWorkspace(user_id=auth.user_id, case_id=case_id)
    graph = _load_graph(ws)

    return [
        {
            "name":        node_name,
            "type":        node.get("entity_type", "UNKNOWN"),
            "description": node.get("description", ""),
        }
        for node_name, node in list(graph.nodes(data=True))[:limit]
    ]


@router.get("/relationships")
async def relationships(
    case_id: str,
    limit: int = 100,
    auth: AuthContext = Depends(get_current_user),
):
    """Return relationships from a case's knowledge graph."""
    await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)
    ws    = UserWorkspace(user_id=auth.user_id, case_id=case_id)
    graph = _load_graph(ws)

    return [
        {
            "source":      source,
            "target":      target,
            "description": edge.get("description", ""),
            "weight":      edge.get("weight", 1),
        }
        for source, target, edge in list(graph.edges(data=True))[:limit]
    ]


@router.get("/network")
async def network(
    case_id: str,
    node_limit: int = 500,
    auth: AuthContext = Depends(get_current_user),
):
    """Return the full graph network payload for the interactive explorer.

    Combines nodes + edges into one response that the KnowledgeGraphPage
    expects:  { nodes: [...], edges: [...] }

    Node shape:
        { id, label, type, description }

    Edge shape:
        { id, source, target, weight, description }

    node_limit caps the response for large graphs (default 500 nodes).
    Edges are filtered to only reference included node IDs.
    """
    await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)
    ws    = UserWorkspace(user_id=auth.user_id, case_id=case_id)
    graph = _load_graph(ws)

    # ── Nodes ─────────────────────────────────────────────────────────
    raw_nodes = list(graph.nodes(data=True))[:node_limit]
    included_ids: set[str] = set()
    nodes_payload = []

    for node_name, node_data in raw_nodes:
        clean_name  = node_name.strip('"')
        entity_type = node_data.get("entity_type", "UNKNOWN").strip('"')
        description = node_data.get("description", "").strip('"')

        stable_id = hashlib.md5(clean_name.encode()).hexdigest()[:12]

        included_ids.add(node_name)
        nodes_payload.append({
            "id":          stable_id,
            "label":       clean_name,
            "type":        entity_type,
            "description": description,
            "_raw_name":   node_name,
        })

    name_to_id: dict[str, str] = {
        n["_raw_name"]: n["id"] for n in nodes_payload
    }

    for n in nodes_payload:
        del n["_raw_name"]

    # ── Edges ──────────────────────────────────────────────────────────
    edges_payload = []
    seen_edges: set[tuple] = set()

    for source, target, edge_data in graph.edges(data=True):
        if source not in included_ids or target not in included_ids:
            continue

        dedup_key = tuple(sorted([source, target]))
        if dedup_key in seen_edges:
            continue
        seen_edges.add(dedup_key)

        src_id = name_to_id.get(source)
        tgt_id = name_to_id.get(target)
        if not src_id or not tgt_id:
            continue

        description = edge_data.get("description", "").strip('"')
        weight = edge_data.get("weight", 1)
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            weight = 1.0

        edge_id = hashlib.md5(f"{source}|{target}".encode()).hexdigest()[:12]

        edges_payload.append({
            "id":          edge_id,
            "source":      src_id,
            "target":      tgt_id,
            "weight":      weight,
            "description": description,
        })

    return {
        "case_id": case_id,
        "nodes":   nodes_payload,
        "edges":   edges_payload,
        "meta": {
            "total_nodes":    graph.number_of_nodes(),
            "total_edges":    graph.number_of_edges(),
            "returned_nodes": len(nodes_payload),
            "returned_edges": len(edges_payload),
        },
    }
