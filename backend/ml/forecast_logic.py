"""
Forecast Logic — auth-free decision layer for the cashflow forecaster.

Enterprise Compliance Intelligence Platform

Purpose
-------
Houses the three decision functions that were previously defined inline inside
``backend.api.routes.forecast``.  Separating them here follows the same
pattern already used by the rest of the compliance engine:

    reconciliation_engine.py  — engine logic
    backend/api/routes/reconciliation.py  — thin auth/HTTP wrapper

    tax_matcher.py            — engine logic
    backend/api/routes/tax_matching.py    — thin auth/HTTP wrapper

    forecast_logic.py         — engine logic   ← this file
    backend/api/routes/forecast.py        — thin auth/HTTP wrapper

No imports from fastapi, jose, supabase, or backend.auth appear here.
The functions are safe to import in any test environment, including those
without the full server dependency stack installed.

Public API
----------
``_build_latest_feature_row(daily_df)``
    Returns the most-recent feature vector as a numpy array, or None when the
    daily series is too short to produce any feature row (< 14 days).

``build_insufficient_history_response()``
    Returns the exact dict that the route returns for a thin-data workspace.

``_load_meta(artifacts_dir)``
    Loads forecaster_meta.json; raises FileNotFoundError with a consistent
    message if the file is absent.

``_load_models(artifacts_dir)``
    Loads all three quantile joblib model files; raises FileNotFoundError if
    any is missing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from backend.ml.features import FEATURE_COLUMNS, build_feature_table


# ---------------------------------------------------------------------------
# Feature row builder
# ---------------------------------------------------------------------------

def _build_latest_feature_row(daily_df) -> "np.ndarray | None":
    """Extract the single most-recent feature vector from the daily series.

    ``build_feature_table`` drops the last ``horizon_days`` rows because those
    rows have no valid lookahead target — but at inference time we *want* the
    most recent fully-observable row, regardless of whether a future target
    exists.  We therefore call ``build_feature_table`` with ``horizon_days=1``
    (minimum valid horizon) so the last row of the input becomes the last row
    of the feature table, then take that final row.

    Returns None when the series is too short to produce any feature row
    (fewer than _MIN_HISTORY = 14 days).
    """
    ft = build_feature_table(daily_df, horizon_days=1)
    if ft.features.empty:
        return None
    # The last row is the most recent day with a full feature vector.
    latest = ft.features.iloc[[-1]][FEATURE_COLUMNS].to_numpy(dtype=float)
    return latest   # shape (1, n_features)


# ---------------------------------------------------------------------------
# Thin-data response constructor
# ---------------------------------------------------------------------------

def build_insufficient_history_response() -> dict[str, Any]:
    """Return the canonical thin-data response dict.

    This is the exact shape the route returns (HTTP 200) when the workspace
    has fewer than 14 days of dated cashflow history.  Centralising it here
    means the route and any test can both import the same dict rather than
    relying on string literals in two places.
    """
    return {
        "forecast_available": False,
        "reason": "insufficient historical data",
    }


# ---------------------------------------------------------------------------
# Artifact loaders
# ---------------------------------------------------------------------------

def _load_meta(artifacts_dir: Path) -> dict[str, Any]:
    """Load forecaster_meta.json.  Raises FileNotFoundError if absent."""
    meta_path = artifacts_dir / "forecaster_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"No trained models found at {artifacts_dir}. "
            "Run scripts/train_forecaster.py before calling this endpoint."
        )
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _load_models(artifacts_dir: Path) -> dict[str, Any]:
    """Load the three quantile models.  Raises FileNotFoundError if any is missing."""
    models: dict[str, Any] = {}
    for name in ("p10", "p50", "p90"):
        path = artifacts_dir / f"forecaster_{name}.joblib"
        if not path.exists():
            raise FileNotFoundError(
                f"Model file missing: {path}. "
                "Run scripts/train_forecaster.py to (re-)train the forecaster."
            )
        models[name] = joblib.load(path)
    return models
