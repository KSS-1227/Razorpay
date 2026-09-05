"""
Workspace-aware cashflow forecast route.

Endpoint
--------
    POST /api/workspace/{case_id}/forecast

Loads the three pre-trained quantile models (Part 3) from the artifacts
directory, builds today's feature row from the workspace's current cashflow
history (Parts 1 + 2), and returns a point forecast with an 80 % confidence
interval.

Same auth / ownership-check pattern as reconciliation.py and tax_matching.py.
NOT a training endpoint — models are loaded from disk, not re-trained on
request.

Decision logic lives in backend.ml.forecast_logic (no auth dependency),
following the same pattern as reconciliation_engine / tax_matcher.

Response shapes
---------------
Normal (≥ 14 days of dated history and models present):

    {
        "forecast_net_cashflow": float,   # p50 point forecast
        "lower_bound":           float,   # p10 lower confidence bound
        "upper_bound":           float,   # p90 upper confidence bound
        "horizon_days":          int,     # forecast window (from meta.json)
        "model_trained_on": {
            "n_training_rows": int,
            "training_date":   str,       # ISO-8601 UTC
        },
        "low_data_warning":      bool,    # true when n_training_rows < 30
    }

Insufficient history (fewer than 14 dated days — can't build one feature row):

    {
        "forecast_available": false,
        "reason":             "insufficient historical data"
    }

Models not yet trained:

    HTTP 404  {"detail": "No trained models found …"}

This mirrors the "unresolved" status pattern in reconciliation_engine.py and
tax_matcher.py — an honest "can't answer" is a design feature, not a bug.
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
from backend.ml.forecast_logic import (
    _build_latest_feature_row,
    _load_meta,
    _load_models,
    build_insufficient_history_response,
)

router = APIRouter(
    prefix="/workspace",
    tags=["Forecast"],
)

# Default artifacts directory — same location Part 3 writes to.
# Resolved relative to this file: backend/api/routes/ → ../../ml/artifacts/
_DEFAULT_ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "ml" / "artifacts"


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class ForecastRequest(BaseModel):
    # Optional override for the working directory.  Only accepted when the
    # resolved path is inside the caller's own workspace root.
    working_dir: str | None = None
    # Optional override for the artifacts directory (useful for testing or
    # when models are stored in a non-default location).
    artifacts_dir: str | None = None


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/{case_id}/forecast")
async def forecast_workspace(
    case_id: str,
    request: ForecastRequest | None = None,
    auth: AuthContext = Depends(get_current_user),
):
    """Return a short-horizon cashflow forecast for a single case workspace.

    - ``case_id`` comes from the path; ``user_id`` from the JWT.
    - Ownership is verified before any graph or model access.
    - Models must have been pre-trained via ``scripts/train_forecaster.py``.
    - Returns ``{"forecast_available": false, …}`` (HTTP 200) rather than a
      500 when the workspace has insufficient history — consistent with the
      "unresolved" design pattern across the compliance engine.
    """
    try:
        await _verify_case_ownership(case_id=case_id, user_id=auth.user_id)

        # ------------------------------------------------------------------
        # Resolve paths
        # ------------------------------------------------------------------
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

        artifacts_dir = _DEFAULT_ARTIFACTS_DIR
        if request and request.artifacts_dir:
            artifacts_dir = Path(request.artifacts_dir).resolve()

        # ------------------------------------------------------------------
        # Load models + meta (404 if not yet trained)
        # ------------------------------------------------------------------
        try:
            meta   = _load_meta(artifacts_dir)
            models = _load_models(artifacts_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        # ------------------------------------------------------------------
        # Part 1: extract cashflow series and aggregate to daily
        # ------------------------------------------------------------------
        extractor = CashflowExtractor(workspace_id=case_id, working_dir=working_dir)
        events    = await extractor.extract()
        daily_df  = aggregate_daily(events)

        # ------------------------------------------------------------------
        # Part 2: build the most-recent feature row
        # ------------------------------------------------------------------
        feature_row = _build_latest_feature_row(daily_df)

        if feature_row is None:
            # Fewer than 14 dated days — can't compute any feature.
            # Return an honest "can't answer" (200) rather than fabricating.
            logger.info(
                "Forecast unavailable — case=%s has insufficient history "
                "(%d dated events)",
                case_id,
                len(events),
            )
            return build_insufficient_history_response()

        # ------------------------------------------------------------------
        # Predict with all three quantile models
        # ------------------------------------------------------------------
        p10 = float(models["p10"].predict(feature_row)[0])
        p50 = float(models["p50"].predict(feature_row)[0])
        p90 = float(models["p90"].predict(feature_row)[0])

        return {
            "forecast_net_cashflow": round(p50, 4),
            "lower_bound":           round(p10, 4),
            "upper_bound":           round(p90, 4),
            "horizon_days":          meta["horizon_days"],
            "model_trained_on": {
                "n_training_rows": meta["n_training_rows"],
                "training_date":   meta["training_date"],
            },
            "low_data_warning": meta["low_data_warning"],
        }

    except HTTPException:
        raise
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Forecast 500 — case=%s user=%s\n%s", case_id, auth.user_id, tb)
        raise HTTPException(status_code=500, detail=str(exc) or repr(exc)) from exc
