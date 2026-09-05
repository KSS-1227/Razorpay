"""
Workspace-aware tax-line matching route.

Endpoint
--------
    POST /api/workspace/{case_id}/tax-match

For each TAX_LINE_ITEM in the case's knowledge graph, resolves its HSN_CODE
neighbor and that code's expected TAX_RATE from an ingested rate-schedule
document, then compares against the applied rate on the line item itself.
Returns a matched / exception / unresolved summary.

Pure graph traversal + regex (no LLM), same as the reconciliation endpoint.
"""
from __future__ import annotations

import logging
import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.services.case_service import get_case as _verify_case_ownership
from backend.auth.workspace import UserWorkspace
from backend.compliance.tax_matcher import TaxMatcher

router = APIRouter(
    prefix="/workspace",
    tags=["Tax Matching"],
)


class TaxMatchRequest(BaseModel):
    # Optional override for the directory holding kv_store_text_chunks.json.
    # Only honored when it resolves inside the caller's own workspace root.
    working_dir: str | None = None


@router.post("/{case_id}/tax-match")
async def tax_match_workspace(
    case_id: str,
    request: TaxMatchRequest | None = None,
    auth: AuthContext = Depends(get_current_user),
):
    """Match applied tax rates against expected rates for a single case workspace.

    - case_id comes from the path, user_id from the JWT.
    - Ownership is verified before any graph access.
    - The workspace path is resolved server-side; a client-supplied working_dir
      is only accepted when it points inside this user's own workspace.
    """
    try:
        await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)

        workspace = UserWorkspace(user_id=auth.user_id, case_id=case_id)
        working_dir = str(workspace.working)

        if request and request.working_dir:
            candidate = Path(request.working_dir).resolve()
            if not candidate.is_relative_to(workspace.root.resolve()):
                raise HTTPException(
                    status_code=400,
                    detail="working_dir must be inside the case workspace",
                )
            working_dir = str(candidate)

        engine = TaxMatcher(workspace_id=case_id, working_dir=working_dir)
        return await engine.match()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("TaxMatch 500 — case=%s user=%s\n%s", case_id, auth.user_id, tb)
        raise HTTPException(status_code=500, detail=str(exc) or repr(exc)) from exc
