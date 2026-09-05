"""
tests/test_forecast_route.py

Single scenario tested in depth:

    A workspace with too little dated history (< 14 days) POSTs to
    /api/workspace/{case_id}/forecast and receives:

        HTTP 200  {"forecast_available": false, "reason": "insufficient historical data"}

    NOT a 500.  NOT a fabricated forecast number.

Why this test matters
---------------------
A forecaster that admits it cannot answer on thin data is more credible than
one that always returns a confident-looking number.  This test locks in the
"unresolved" design pattern that runs through reconciliation_engine.py,
tax_matcher.py, and now the forecast route.

Test architecture
-----------------
All assertions import directly from backend.ml.forecast_logic, which has no
auth dependency chain (no fastapi, jose, supabase, or backend.auth imports).
This is the same separation-of-concerns pattern used across the compliance
engine — the engine logic is testable in isolation; the route is a thin wrapper
that is tested in integration with real auth credentials.

Test classes
------------
TestBuildLatestFeatureRowGate
    Unit tests on _build_latest_feature_row — the exact gate that returns None
    for thin data, preventing model.predict() from ever being called.

TestThinDataResponseShape
    Integration tests that call _build_latest_feature_row + aggregate_daily +
    build_insufficient_history_response together, verifying the full response
    dict shape at every boundary.

TestLoadHelpers
    Verify _load_meta raises FileNotFoundError with the correct message on a
    missing file, and that a valid meta.json contains all required keys.
"""
from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# All imports from backend.ml.forecast_logic — no auth chain, no jose/supabase
# ---------------------------------------------------------------------------
from backend.ml.forecast_logic import (
    _build_latest_feature_row,
    _load_meta,
    _load_models,
    build_insufficient_history_response,
)
from backend.compliance.cashflow_extractor import aggregate_daily
from backend.ml.features import FEATURE_COLUMNS


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_short_daily(n: int) -> pd.DataFrame:
    """Return a gapless daily_df with n rows — too short for any feature row."""
    start = date(2024, 1, 1)
    return pd.DataFrame({
        "date":     [start + timedelta(days=i) for i in range(n)],
        "net_flow": [float(500 * (i + 1)) for i in range(n)],
        "n_events": [1] * n,
    })


def _make_meta(tmp_dir: Path) -> dict:
    """Write a minimal forecaster_meta.json and return the dict."""
    meta = {
        "training_date":    "2026-09-05T06:00:00+00:00",
        "horizon_days":     7,
        "n_training_rows":  35,
        "n_test_rows":      9,
        "mae":              1234.56,
        "calibration_pct":  62.5,
        "low_data_warning": False,
        "model_paths":      {},
    }
    (tmp_dir / "forecaster_meta.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )
    return meta


def _events_from_daily(n: int) -> list[dict]:
    """Build the event list that aggregate_daily would receive for n days."""
    start = date(2024, 1, 1)
    return [
        {
            "date":        (start + timedelta(days=i)).isoformat(),
            "amount":      1000.0,
            "direction":   "inflow",
            "source_type": "settlement",
            "node_id":     f"n{i}",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# TestBuildLatestFeatureRowGate
#
# _build_latest_feature_row is the sole gate between 'call the model' and
# 'return forecast_available=False'.  These tests verify it holds for every
# thin-data case.
# ---------------------------------------------------------------------------

class TestBuildLatestFeatureRowGate:

    def test_zero_events_returns_none(self):
        """Empty workspace — gate returns None, no model call possible."""
        assert _build_latest_feature_row(_make_short_daily(0)) is None

    def test_five_events_returns_none(self):
        """5 days < 14-day minimum — gate returns None."""
        assert _build_latest_feature_row(_make_short_daily(5)) is None

    def test_thirteen_events_returns_none(self):
        """13 days: one below the 14-day minimum — gate still returns None."""
        assert _build_latest_feature_row(_make_short_daily(13)) is None

    def test_fifteen_events_returns_array(self):
        """
        15 rows: history guard (14) satisfied + horizon=1 → 1 feature row.
        Gate returns a real array, not None — model.predict() would be called.
        """
        result = _build_latest_feature_row(_make_short_daily(15))
        assert result is not None, (
            "Expected a feature vector for 15-row series, got None"
        )

    def test_none_has_no_shape(self):
        """None return cannot be array-like — model.predict(None) would crash."""
        result = _build_latest_feature_row(_make_short_daily(7))
        assert not hasattr(result, "shape"), (
            "Gate returned an array-like for thin data — model would be called"
        )

    def test_sufficient_data_correct_shape(self):
        """20-row series → (1, 9) feature vector, one row per FEATURE_COLUMNS."""
        result = _build_latest_feature_row(_make_short_daily(20))
        assert result is not None
        assert result.shape == (1, len(FEATURE_COLUMNS))


# ---------------------------------------------------------------------------
# TestThinDataResponseShape
#
# Verify the full response dict produced when history is insufficient,
# using the real imported functions — not inline reproductions.
# ---------------------------------------------------------------------------

class TestThinDataResponseShape:

    def _response_for(self, n_events: int) -> dict:
        """
        Run the exact logic path from forecast_workspace for a thin-data case:
          aggregate_daily → _build_latest_feature_row → None
          → build_insufficient_history_response()
        """
        daily_df = aggregate_daily(_events_from_daily(n_events))
        feature_row = _build_latest_feature_row(daily_df)
        if feature_row is None:
            return build_insufficient_history_response()
        # Should not be reached for thin data; return sentinel so tests fail clearly
        return {"forecast_available": True, "SHOULD_NOT_HAPPEN": True}

    def test_returns_dict(self):
        assert isinstance(self._response_for(5), dict)

    def test_forecast_available_is_false(self):
        """The central guarantee: thin data → forecast_available=False."""
        result = self._response_for(5)
        assert result["forecast_available"] is False, (
            f"forecast_available is not False: {result}"
        )

    def test_reason_key_present(self):
        assert "reason" in self._response_for(5)

    def test_reason_mentions_insufficient(self):
        assert "insufficient" in self._response_for(5)["reason"].lower()

    def test_no_forecast_net_cashflow(self):
        """A fabricated point forecast must not appear."""
        assert "forecast_net_cashflow" not in self._response_for(5), (
            "Thin-data response must not contain a forecast number"
        )

    def test_no_lower_bound(self):
        assert "lower_bound" not in self._response_for(5)

    def test_no_upper_bound(self):
        assert "upper_bound" not in self._response_for(5)

    def test_no_model_trained_on(self):
        assert "model_trained_on" not in self._response_for(5)

    def test_exactly_two_keys(self):
        """
        Thin-data response must be exactly {forecast_available, reason}.
        Extra keys risk leaking a partial or fabricated result.
        """
        result = self._response_for(5)
        assert set(result.keys()) == {"forecast_available", "reason"}, (
            f"Unexpected keys: {set(result.keys())}"
        )

    def test_zero_events(self):
        """Zero events → unavailable, not a crash."""
        assert self._response_for(0)["forecast_available"] is False

    def test_thirteen_events(self):
        """13 events: one below the 14-day minimum — still unavailable."""
        assert self._response_for(13)["forecast_available"] is False

    def test_gate_not_tripped_for_sufficient_data(self):
        """
        20+ events: gate must NOT fire — valid workspaces get real forecasts.
        """
        result = self._response_for(20)
        assert result.get("forecast_available") is not False, (
            "20-event workspace incorrectly treated as insufficient"
        )

    def test_response_is_canonical(self):
        """
        build_insufficient_history_response() must return the identical dict
        regardless of how many times it is called — no mutable state.
        """
        r1 = build_insufficient_history_response()
        r2 = build_insufficient_history_response()
        assert r1 == r2
        assert r1 is not r2   # fresh dict each call, no shared reference


# ---------------------------------------------------------------------------
# TestLoadHelpers
# ---------------------------------------------------------------------------

class TestLoadHelpers:

    def test_load_meta_raises_for_missing_file(self):
        """Missing forecaster_meta.json → FileNotFoundError, not silent None."""
        empty_dir = Path(tempfile.mkdtemp())
        with pytest.raises(FileNotFoundError, match="No trained models found"):
            _load_meta(empty_dir)

    def test_load_meta_error_message_mentions_script(self):
        """Error message must guide the user to the training script."""
        empty_dir = Path(tempfile.mkdtemp())
        with pytest.raises(FileNotFoundError, match="train_forecaster"):
            _load_meta(empty_dir)

    def test_load_meta_returns_all_required_keys(self):
        """A valid meta.json must contain the six keys the route reads."""
        tmp = Path(tempfile.mkdtemp())
        _make_meta(tmp)
        loaded = _load_meta(tmp)
        for key in ("horizon_days", "n_training_rows", "training_date",
                    "low_data_warning", "mae", "calibration_pct"):
            assert key in loaded, f"meta key '{key}' missing"

    def test_load_models_raises_for_missing_file(self):
        """Missing model files → FileNotFoundError, not silent None."""
        empty_dir = Path(tempfile.mkdtemp())
        with pytest.raises(FileNotFoundError, match="Model file missing"):
            _load_models(empty_dir)

    def test_load_models_error_message_mentions_script(self):
        """Error message must guide the user to the training script."""
        empty_dir = Path(tempfile.mkdtemp())
        with pytest.raises(FileNotFoundError, match="train_forecaster"):
            _load_models(empty_dir)
