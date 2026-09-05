"""
Workspace-aware query route.

Replaces query.py for authenticated requests.
All GraphRAG retrieval runs inside the user's workspace:
    data/users/{user_id}/cases/{case_id}/working/
    data/users/{user_id}/cases/{case_id}/output/

The original query.py is NOT modified.
"""
from __future__ import annotations

import logging
import traceback
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.services.case_service import get_case as _verify_case_ownership
from backend.services.workspace_document_service import WorkspaceDocumentService

router = APIRouter(
    prefix="/query",
    tags=["GraphRAG Query"],
)


class QueryRequest(BaseModel):
    case_id:  str
    session_id: UUID | None = None
    question: str  = Field(..., min_length=3)
    top_k:    int  = Field(default=10, ge=1, le=50)


@router.post("/")
async def ask_question(
    request: QueryRequest,
    auth: AuthContext = Depends(get_current_user),
):
    """Run a GraphRAG query against the user's case workspace.

    - case_id is taken from the request body and the user_id from the JWT.
    - The workspace path data/users/{user_id}/cases/{case_id}/ is resolved
      server-side — no path is accepted from the client.
    """
    try:
        await _verify_case_ownership(case_id=request.case_id, user_id=auth.user_id)
        svc    = WorkspaceDocumentService(
            user_id=auth.user_id,
            case_id=request.case_id,
        )
        session_id = str(request.session_id or uuid.uuid4())
        result = await svc.query(
            question=request.question,
            top_k=request.top_k,
            session_id=session_id,
        )
        return {
            "success":  True,
            "question": request.question,
            "case_id":  request.case_id,
            "session_id": session_id,
            "result":   result,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Query 500 — case=%s user=%s\n%s", request.case_id, auth.user_id, tb)
        raise HTTPException(status_code=500, detail=str(exc) or repr(exc)) from exc
