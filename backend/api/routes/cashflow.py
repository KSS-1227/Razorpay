"""
Workspace-aware cashflow extraction route.

Endpoint
--------
    POST /api/workspace/{case_id}/cashflow

For every INVOICE_AMOUNT, CONTRACT_AMOUNT, and SETTLEMENT_AMOUNT node in the
case's knowledge graph, resolves the associated date and amount, emits one
row per event, and returns both the raw event list and a gapless daily
aggregate.

Pure graph traversal + regex (no LLM), same as the reconciliation and
tax-matching endpoints.
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
from backend.compliance.cashflow_extractor import CashflowExtractor, aggregate_daily

router = APIRouter(
    prefix="/workspace",
    tags=["Cashflow"],
)


class CashflowRequest(BaseModel):
    # Optional override for the directory holding kv_store_text_chunks.json.
    # Only accepted when the resolved path is inside the caller's own workspace
    # root — the server-resolved working dir is used otherwise.
    working_dir: str | None = None


@router.post("/{case_id}/cashflow")
async def cashflow_workspace(
    case_id: str,
    request: CashflowRequest | None = None,
    auth: AuthContext = Depends(get_current_user),
):
    """Extract a daily net-cash-flow time series for a single case workspace.

    - ``case_id`` comes from the path; ``user_id`` from the JWT.
    - Ownership is verified before any graph access.
    - The workspace path is resolved server-side; a client-supplied
      ``working_dir`` is only honoured when it falls inside this user's own
      workspace root.

    Response shape::

        {
            "workspace_id": str,
            "total_events": int,
            "events": [
                {
                    "date":        "YYYY-MM-DD",
                    "amount":      float,
                    "direction":   "outflow" | "inflow",
                    "source_type": "invoice" | "settlement",
                    "node_id":     str,
                }
            ],
            "daily_series": [
                {
                    "date":      "YYYY-MM-DD",
                    "net_flow":  float,
                    "n_events":  int,
                }
            ],
        }
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

        extractor = CashflowExtractor(workspace_id=case_id, working_dir=working_dir)
        events = await extractor.extract()

        # Build the daily aggregate and serialise to plain dicts for JSON.
        df = aggregate_daily(events)
        daily_series = [
            {
                "date":     str(row.date),      # date object → "YYYY-MM-DD"
                "net_flow": row.net_flow,
                "n_events": int(row.n_events),
            }
            for row in df.itertuples(index=False)
        ]

        return {
            "workspace_id": case_id,
            "total_events": len(events),
            "events":       events,
            "daily_series": daily_series,
        }

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Cashflow 500 — case=%s user=%s\n%s", case_id, auth.user_id, tb)
        raise HTTPException(status_code=500, detail=str(exc) or repr(exc)) from exc
