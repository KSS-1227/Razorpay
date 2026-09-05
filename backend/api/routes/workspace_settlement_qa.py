"""
Settlement Q&A route.

Thin domain-specific wrapper around the existing workspace query path.
All GraphRAG retrieval is delegated to WorkspaceDocumentService.query()
unchanged — no retrieval logic is duplicated here.

Endpoint
--------
POST /api/workspace/{id}/settlement-qa

Accepts the same fields as /api/query/'s QueryRequest except case_id, which
is a path parameter here rather than a body field.

Injects a settlement-domain addendum into the LLM system prompt *after*
vector retrieval completes, so the raw question text reaches the embedding
step unmodified.

Returns the same evidence/citation envelope as /api/query/.
"""
from __future__ import annotations

import logging
import traceback
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.services.case_service import get_case as _verify_case_ownership
from backend.services.workspace_document_service import WorkspaceDocumentService

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Settlement Q&A"],
)

# ---------------------------------------------------------------------------
# Settlement domain addendum — injected into the LLM system prompt only,
# after vector retrieval completes.  The raw question is never modified.
# ---------------------------------------------------------------------------
_SETTLEMENT_PREAMBLE = (
    "You are a settlement and payout analyst. "
    "Answer using settlement/payout terminology (settlement IDs, payout status, "
    "fee deductions, UTR numbers, net amounts, processing dates). "
    "If the question is not about a settlement or payout, say so clearly rather "
    "than guessing or answering from unrelated context."
)


class QueryRequest(BaseModel):
    session_id: UUID | None = None
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=10, ge=1, le=50)


@router.post("/workspace/{case_id}/settlement-qa")
async def settlement_qa(
    case_id: str,
    request: QueryRequest,
    auth: AuthContext = Depends(get_current_user),
):
    """Run a settlement-domain GraphRAG query against the user's case workspace.

    Same response envelope and evidence/citation structure as POST /api/query/.
    case_id is a path parameter here (not a body field). A settlement-domain
    addendum is injected into the LLM system prompt after retrieval; the
    question reaches the vector search step unmodified.
    """
    try:
        await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)
        svc = WorkspaceDocumentService(
            user_id=auth.user_id,
            case_id=case_id,
        )
        session_id = str(request.session_id or uuid.uuid4())
        result = await svc.query(
            question=request.question,
            top_k=request.top_k,
            session_id=session_id,
            system_prompt_addendum=_SETTLEMENT_PREAMBLE,
        )
        return {
            "success": True,
            "question": request.question,
            "case_id": case_id,
            "session_id": session_id,
            "result": result,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(
            "Settlement QA 500 — case=%s user=%s\n%s",
            case_id, auth.user_id, tb,
        )
        raise HTTPException(status_code=500, detail=str(exc) or repr(exc)) from exc
