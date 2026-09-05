"""
Unit tests for backend/compliance/tax_matcher.py

Covers:
1. Matched case — applied rate equals expected rate
2. Rate-mismatch exception — applied rate differs from expected rate
3. Unresolved — TAX_LINE_ITEM has no HSN_CODE neighbor
4. Ambiguity — HSN_CODE has two conflicting TAX_RATE neighbors (deterministic
   choice, ambiguity recorded in reason)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def _node(entity_type: str, description: str, source_id: str = "") -> dict:
    return {"entity_type": entity_type, "description": description, "source_id": source_id}


def _make_engine():
    """Return a TaxMatcher with DB methods patched out."""
    with patch("backend.compliance.reconciliation_engine._get_pool"):
        from backend.compliance.tax_matcher import TaxMatcher
        eng = TaxMatcher.__new__(TaxMatcher)
        eng.workspace_id = "ws-tax-test"
        eng.working_dir = "/tmp/fake"
        # Build the delegate the same way __init__ does, but without DB
        from backend.compliance.reconciliation_engine import ReconciliationEngine as _RE
        delegate = _RE.__new__(_RE)
        delegate.workspace_id = "ws-tax-test"
        delegate.working_dir = "/tmp/fake"
        eng._delegate = delegate
        return eng


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _run_match(nodes, adjacency):
    eng = _make_engine()
    eng._delegate._load_nodes = AsyncMock(return_value=nodes)
    eng._delegate._load_adjacency = AsyncMock(return_value=adjacency)
    eng._delegate._load_text_chunks = MagicMock(return_value={})
    return _run(eng.match())


# ---------------------------------------------------------------------------
# 1. Matched case
# ---------------------------------------------------------------------------

class TestTaxMatcherMatched:
    """Applied rate equals expected rate — status must be 'matched'."""

    def _build(self):
        nodes = {
            "tli1": _node("TAX_LINE_ITEM", "Consulting services: \u20b940,000 @ 18%"),
            "hsn1": _node("HSN_CODE",      "HSN 998314"),
            "rate1": _node("TAX_RATE",     "18%"),  # expected (linked to HSN)
        }
        adjacency = {
            "tli1":  {"hsn1"},
            "hsn1":  {"tli1", "rate1"},
            "rate1": {"hsn1"},
        }
        return nodes, adjacency

    def test_status_matched(self):
        summary = _run_match(*self._build())
        assert summary["matched"] == 1
        assert summary["exceptions"] == 0
        assert summary["unresolved"] == 0

    def test_match_rate_100(self):
        summary = _run_match(*self._build())
        assert summary["match_rate"] == "100%"

    def test_result_row_shape(self):
        summary = _run_match(*self._build())
        row = summary["results"][0]
        for key in ("item_id", "hsn_id", "status", "reason", "applied_rate",
                    "expected_rate", "source_files"):
            assert key in row, f"Key '{key}' missing from result row"
        assert row["applied_rate"] == 18.0
        assert row["expected_rate"] == 18.0


# ---------------------------------------------------------------------------
# 2. Rate-mismatch exception
# ---------------------------------------------------------------------------

class TestTaxMatcherException:
    """Applied rate differs from expected rate — status must be 'exception'."""

    def _build(self):
        nodes = {
            "tli1": _node("TAX_LINE_ITEM", "Software license: \u20b960,000 @ 12%"),
            "hsn1": _node("HSN_CODE",      "HSN 998313"),
            "rate1": _node("TAX_RATE",     "18%"),  # expected by rate schedule
        }
        adjacency = {
            "tli1":  {"hsn1"},
            "hsn1":  {"tli1", "rate1"},
            "rate1": {"hsn1"},
        }
        return nodes, adjacency

    def test_status_exception(self):
        summary = _run_match(*self._build())
        assert summary["exceptions"] == 1
        assert summary["matched"] == 0

    def test_reason_contains_both_rates(self):
        summary = _run_match(*self._build())
        row = summary["results"][0]
        assert row["status"] == "exception"
        assert "12.0%" in row["reason"]
        assert "18.0%" in row["reason"]

    def test_rates_recorded_correctly(self):
        summary = _run_match(*self._build())
        row = summary["results"][0]
        assert row["applied_rate"] == 12.0
        assert row["expected_rate"] == 18.0


# ---------------------------------------------------------------------------
# 3. Unresolved — no HSN_CODE link
# ---------------------------------------------------------------------------

class TestTaxMatcherUnresolvedNoHSN:
    """TAX_LINE_ITEM with no HSN_CODE neighbor must be 'unresolved', not dropped."""

    def _build(self):
        nodes = {
            "tli1":  _node("TAX_LINE_ITEM", "Freight charges: \u20b95,000 @ 5%"),
            "rate1": _node("TAX_RATE",      "5%"),
            # No HSN_CODE node in the graph at all
        }
        adjacency = {
            "tli1":  {"rate1"},
            "rate1": {"tli1"},
        }
        return nodes, adjacency

    def test_status_unresolved(self):
        summary = _run_match(*self._build())
        assert summary["unresolved"] == 1
        assert summary["matched"] == 0
        assert summary["exceptions"] == 0

    def test_reason_mentions_hsn(self):
        summary = _run_match(*self._build())
        row = summary["results"][0]
        assert row["status"] == "unresolved"
        assert "HSN" in row["reason"] or "hsn" in row["reason"].lower()

    def test_item_not_silently_dropped(self):
        summary = _run_match(*self._build())
        assert summary["total"] == 1
        assert len(summary["results"]) == 1


# ---------------------------------------------------------------------------
# 4. Ambiguity — HSN_CODE has two conflicting TAX_RATE neighbors
# ---------------------------------------------------------------------------

class TestTaxMatcherAmbiguousRate:
    """HSN_CODE linked to two TAX_RATE nodes: deterministic choice, reason recorded."""

    def _build(self):
        # rate_b < rate_c lexicographically — rate_b (18%) must be chosen as expected.
        # Applied rate is parsed from the line item description: 18%.
        nodes = {
            "tli1":   _node("TAX_LINE_ITEM", "IT services: \u20b980,000 @ 18%"),
            "hsn1":   _node("HSN_CODE",      "HSN 998315"),
            "rate_b": _node("TAX_RATE",      "18%"),  # expected candidate 1 (lexic. first)
            "rate_c": _node("TAX_RATE",      "28%"),  # expected candidate 2
        }
        adjacency = {
            "tli1":   {"hsn1"},
            "hsn1":   {"tli1", "rate_b", "rate_c"},
            "rate_b": {"hsn1"},
            "rate_c": {"hsn1"},
        }
        return nodes, adjacency

    def test_deterministic_choice(self):
        """Running match twice must return the same expected_rate both times."""
        eng = _make_engine()
        nodes, adjacency = self._build()
        eng._delegate._load_nodes = AsyncMock(return_value=nodes)
        eng._delegate._load_adjacency = AsyncMock(return_value=adjacency)
        eng._delegate._load_text_chunks = MagicMock(return_value={})

        r1 = _run(eng.match())
        r2 = _run(eng.match())
        assert r1["results"][0]["expected_rate"] == r2["results"][0]["expected_rate"]

    def test_lexicographic_winner(self):
        """'rate_b' < 'rate_c' lexicographically — rate_b (18%) must be chosen."""
        summary = _run_match(*self._build())
        row = summary["results"][0]
        assert row["expected_rate"] == 18.0

    def test_ambiguity_recorded_in_reason(self):
        summary = _run_match(*self._build())
        row = summary["results"][0]
        # Ambiguity note must appear in reason (matched or exception)
        assert row["reason"] is not None
        assert "Multiple TAX_RATE" in row["reason"]

    def test_status_matched_when_rates_agree(self):
        """applied=18%, expected (rate_b)=18% — must be matched despite ambiguity."""
        summary = _run_match(*self._build())
        row = summary["results"][0]
        assert row["status"] == "matched"


# ---------------------------------------------------------------------------
# 5. Route — FileNotFoundError surfaces as HTTP 404
# ---------------------------------------------------------------------------

class TestTaxMatchingRoute:
    def test_404_when_graph_not_found(self):
        """FileNotFoundError from TaxMatcher.match() must become HTTP 404."""
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        import backend.api.routes.tax_matching as mod
        from backend.auth.middleware.jwt_middleware import AuthContext

        fake_engine = MagicMock()
        fake_engine.match = AsyncMock(side_effect=FileNotFoundError("No graph"))

        with (
            patch.object(mod, "_verify_case_ownership", new=AsyncMock()),
            patch.object(mod, "TaxMatcher", return_value=fake_engine),
        ):
            app = FastAPI()
            app.include_router(
                mod.router,
                prefix="/api",
                dependencies=[
                    Depends(lambda: AuthContext(user_id="u1", email="x@x.com", role="user"))
                ],
            )
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/api/workspace/case-abc/tax-match",
                json={},
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 404
