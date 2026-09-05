"""
Workspace-aware report route.

Replaces report.py for authenticated requests.
All data is read from:
    data/users/{user_id}/cases/{case_id}/output/

The original report.py is NOT modified.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.workspace import UserWorkspace
from backend.services.workspace_document_service import WorkspaceDocumentService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/report",
    tags=["Compliance Report"],
)


class ReportRequest(BaseModel):
    case_id:  str
    question: str
    top_k:    int = 10


@router.post("/")
async def generate_report(
    request: ReportRequest,
    auth: AuthContext = Depends(get_current_user),
):
    """Generate a compliance report for a case."""
    ws = UserWorkspace(user_id=auth.user_id, case_id=request.case_id)

    if not ws.graph_exists():
        raise HTTPException(
            status_code=404,
            detail="Knowledge Graph not found for this case. Upload and process documents first.",
        )

    # Run workspace-scoped query (graph is loaded once inside the service)
    try:
        svc    = WorkspaceDocumentService(user_id=auth.user_id, case_id=request.case_id)
        result = await svc.query(request.question, top_k=request.top_k)
        graph_summary = svc.graph_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "user_id":      auth.user_id,
        "case_id":      request.case_id,
        "knowledge_graph": {
            "nodes":               graph_summary.get("nodes", 0),
            "edges":               graph_summary.get("edges", 0),
            "entity_distribution": graph_summary.get("entity_types", {}),
        },
        "query":   request.question,
        "answer":  result["answer"],
        "evidence": result.get("evidence", {}),
        "prototype": {
            "engine":     "MMGraphRAG",
            "multimodal": True,
            "retrieval":  "GraphRAG",
        },
    }

    try:
        ws.report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Could not persist report.json for case=%s: %s", request.case_id, exc)

    return {"success": True, "report": report}


@router.get("/{case_id}")
async def get_report(
    case_id: str,
    auth: AuthContext = Depends(get_current_user),
):
    """Return the most recently generated report.json for a case."""
    ws = UserWorkspace(user_id=auth.user_id, case_id=case_id)

    if not ws.report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No report found for this case. Generate one first via POST /api/report/",
        )

    try:
        report = json.loads(ws.report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read report: {exc}") from exc

    return {"success": True, "report": report}
