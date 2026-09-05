"""
Workspace stats route.

GET /api/stats?case_id={case_id}

Returns real RAG precision and LLM cache hit rate for a case.
These values drive the "RAG Precision Score" and "Cache" metric
cards on the frontend Dashboard.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.services.case_service import get_case as _verify_case_ownership
from backend.services.workspace_document_service import WorkspaceDocumentService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stats",
    tags=["Stats"],
)


@router.get("/")
async def get_stats(
    case_id: str = Query(..., description="The case to retrieve stats for"),
    auth: AuthContext = Depends(get_current_user),
):
    """Return real RAG precision and cache hit rate for the given case.

    Response shape::

        {
            "total_queries":  3,
            "rag_precision":  87.4,   // rolling avg confidence %, or null
            "cache_hit_rate": 62.5,   // LLM cache hit %, or null
            "cached_entries": 6
        }

    ``rag_precision`` and ``cache_hit_rate`` are ``null`` until the first
    query is run — the frontend should display "—" in that case.
    """
    try:
        await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    svc = WorkspaceDocumentService(user_id=auth.user_id, case_id=case_id)
    return svc.get_stats()
