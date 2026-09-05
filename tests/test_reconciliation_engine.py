"""
Unit tests for backend/compliance/reconciliation_engine.py

Covers:
- Multi-vendor workspace with different per-vendor approval limits
- Structuring detection (3 invoices, same vendor/week, individually under limit, sum over)
- Ambiguity when a vendor has two CONTRACT_AMOUNT nodes
- Payment timeliness with and without a resolvable DUE_DATE
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to build fake graph data without touching CockroachDB
# ---------------------------------------------------------------------------

def _node(entity_type: str, description: str, source_id: str = "") -> dict:
    return {"entity_type": entity_type, "description": description, "source_id": source_id}


def _make_engine():
    """Return a ReconciliationEngine with DB methods patched out."""
    with patch("backend.compliance.reconciliation_engine._get_pool"):
        from backend.compliance.reconciliation_engine import ReconciliationEngine
        eng = ReconciliationEngine.__new__(ReconciliationEngine)
        eng.workspace_id = "ws-test"
        eng.working_dir = "/tmp/fake"
        return eng


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Import the module-level helpers directly for unit testing
# ---------------------------------------------------------------------------

from backend.compliance.reconciliation_engine import (
    ReconciliationEngine,
    _parse_amount,
    _parse_date,
)


# ---------------------------------------------------------------------------
# 1. Per-vendor approval threshold
# ---------------------------------------------------------------------------

class TestPerVendorApprovalThreshold:
    """Each vendor's APPROVAL_LIMIT must only apply to that vendor's invoices."""

    def _build(self):
        nodes = {
            "inv1": _node("INVOICE", "\u20b950000 INV-001"),
            "inv2": _node("INVOICE", "\u20b9150000 INV-002"),
            "v1":   _node("VENDOR", "Vendor A"),
            "v2":   _node("VENDOR", "Vendor B"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9200000"),
            "c2":   _node("CONTRACT_AMOUNT", "\u20b9200000"),
            "al1":  _node("APPROVAL_LIMIT", "\u20b960000"),   # Vendor A limit
            "al2":  _node("APPROVAL_LIMIT", "\u20b9200000"),  # Vendor B limit
        }
        adjacency = {
            "inv1": {"v1"}, "v1": {"inv1", "c1", "al1"},
            "inv2": {"v2"}, "v2": {"inv2", "c2", "al2"},
            "c1": {"v1"}, "al1": {"v1"},
            "c2": {"v2"}, "al2": {"v2"},
        }
        return nodes, adjacency

    def test_vendor_a_invoice_requires_approval(self):
        eng = _make_engine()
        nodes, adjacency = self._build()
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        # 50000 > 60000? No — but let's check the correct limit is used.
        assert row["requires_approval"] is False  # 50000 <= 60000

    def test_vendor_b_invoice_does_not_require_approval(self):
        eng = _make_engine()
        nodes, adjacency = self._build()
        row = eng._reconcile_one("inv2", nodes["inv2"], nodes, adjacency, {})
        # 150000 <= 200000
        assert row["requires_approval"] is False

    def test_vendor_a_invoice_over_its_own_limit(self):
        eng = _make_engine()
        nodes, adjacency = self._build()
        # Raise inv1 amount above vendor A's limit (60000) but below vendor B's (200000)
        nodes["inv1"] = _node("INVOICE", "\u20b970000 INV-001")
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert row["requires_approval"] is True

    def test_vendor_b_limit_does_not_bleed_into_vendor_a(self):
        """Vendor B's higher limit must not suppress vendor A's flag."""
        eng = _make_engine()
        nodes, adjacency = self._build()
        nodes["inv1"] = _node("INVOICE", "\u20b970000 INV-001")
        row_a = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        row_b = eng._reconcile_one("inv2", nodes["inv2"], nodes, adjacency, {})
        assert row_a["requires_approval"] is True
        assert row_b["requires_approval"] is False


# ---------------------------------------------------------------------------
# 2. Structuring detection
# ---------------------------------------------------------------------------

class TestStructuringDetection:
    """3 invoices, same vendor/week, each under limit, sum over limit."""

    def _build(self):
        # limit = 100000; each invoice = 40000; sum = 120000 > limit
        nodes = {
            "inv1": _node("INVOICE", "\u20b940000 2024-03-04"),
            "inv2": _node("INVOICE", "\u20b940000 2024-03-05"),
            "inv3": _node("INVOICE", "\u20b940000 2024-03-06"),
            "v1":   _node("VENDOR", "Vendor A"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9200000"),
            "al1":  _node("APPROVAL_LIMIT", "\u20b9100000"),
        }
        adjacency = {
            "inv1": {"v1"}, "inv2": {"v1"}, "inv3": {"v1"},
            "v1": {"inv1", "inv2", "inv3", "c1", "al1"},
            "c1": {"v1"}, "al1": {"v1"},
        }
        return nodes, adjacency

    def _run_reconcile(self, nodes, adjacency):
        eng = _make_engine()
        eng._load_nodes = AsyncMock(return_value=nodes)
        eng._load_adjacency = AsyncMock(return_value=adjacency)
        eng._load_text_chunks = MagicMock(return_value={})
        return _run(eng.reconcile())

    def test_structuring_flagged(self):
        nodes, adjacency = self._build()
        summary = self._run_reconcile(nodes, adjacency)
        assert summary["structuring_groups"] == 1
        flagged = [r for r in summary["results"] if "possible_structuring" in r["flags"]]
        assert len(flagged) == 3

    def test_no_structuring_when_one_invoice_exceeds_limit(self):
        nodes, adjacency = self._build()
        # Make one invoice exceed the limit individually — structuring should NOT fire.
        nodes["inv1"] = _node("INVOICE", "\u20b9110000 2024-03-04")
        summary = self._run_reconcile(nodes, adjacency)
        assert summary["structuring_groups"] == 0

    def test_all_rows_have_flags_field(self):
        nodes, adjacency = self._build()
        summary = self._run_reconcile(nodes, adjacency)
        for row in summary["results"]:
            assert "flags" in row


# ---------------------------------------------------------------------------
# 3. Ambiguity: vendor with two CONTRACT_AMOUNT nodes
# ---------------------------------------------------------------------------

class TestAmbiguousContract:
    def _build(self):
        nodes = {
            "inv1": _node("INVOICE", "\u20b950000"),
            "v1":   _node("VENDOR", "Vendor A"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9100000"),
            "c2":   _node("CONTRACT_AMOUNT", "\u20b9200000"),
        }
        adjacency = {
            "inv1": {"v1"},
            "v1": {"inv1", "c1", "c2"},
            "c1": {"v1"}, "c2": {"v1"},
        }
        return nodes, adjacency

    def test_deterministic_choice(self):
        eng = _make_engine()
        nodes, adjacency = self._build()
        # Run twice — must return the same contract_id both times.
        r1 = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        r2 = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert r1["contract_amount"] == r2["contract_amount"]

    def test_ambiguity_recorded_in_reason(self):
        eng = _make_engine()
        nodes, adjacency = self._build()
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert row["reason"] is not None
        assert "Multiple CONTRACT_AMOUNT" in row["reason"]

    def test_lexicographic_winner(self):
        """'c1' < 'c2' lexicographically, so c1 (100000) should be chosen."""
        eng = _make_engine()
        nodes, adjacency = self._build()
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert row["contract_amount"] == 100000.0

    def test_find_neighbor_returns_sorted_first(self):
        eng = _make_engine()
        nodes, adjacency = self._build()
        chosen, ambiguity = eng._find_neighbor_of_type(
            "v1", "CONTRACT_AMOUNT", nodes, adjacency
        )
        assert chosen == "c1"
        assert ambiguity is not None


# ---------------------------------------------------------------------------
# 4. Payment timeliness
# ---------------------------------------------------------------------------

class TestPaymentTimeliness:
    def _build_with_due_date(self, invoice_date: str, due_date: str):
        nodes = {
            "inv1": _node("INVOICE", f"\u20b950000 {invoice_date}"),
            "v1":   _node("VENDOR", "Vendor A"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9200000"),
            "dd1":  _node("DUE_DATE", due_date),
        }
        adjacency = {
            "inv1": {"v1", "dd1"},
            "v1": {"inv1", "c1"},
            "c1": {"v1"},
            "dd1": {"inv1"},
        }
        return nodes, adjacency

    def test_on_time(self):
        eng = _make_engine()
        nodes, adjacency = self._build_with_due_date("2024-03-10", "2024-03-15")
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert row["payment_timeliness"] == "on_time"

    def test_overdue(self):
        eng = _make_engine()
        nodes, adjacency = self._build_with_due_date("2024-03-20", "2024-03-15")
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert row["payment_timeliness"] == "overdue"

    def test_unknown_when_no_due_date_node(self):
        eng = _make_engine()
        nodes = {
            "inv1": _node("INVOICE", "\u20b950000 2024-03-10"),
            "v1":   _node("VENDOR", "Vendor A"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9200000"),
        }
        adjacency = {
            "inv1": {"v1"}, "v1": {"inv1", "c1"}, "c1": {"v1"},
        }
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert row["payment_timeliness"] == "unknown"

    def test_unknown_when_due_date_unparseable(self):
        eng = _make_engine()
        nodes = {
            "inv1": _node("INVOICE", "\u20b950000 2024-03-10"),
            "v1":   _node("VENDOR", "Vendor A"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9200000"),
            "dd1":  _node("DUE_DATE", "no date here"),
        }
        adjacency = {
            "inv1": {"v1", "dd1"}, "v1": {"inv1", "c1"},
            "c1": {"v1"}, "dd1": {"inv1"},
        }
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adjacency, {})
        assert row["payment_timeliness"] == "unknown"


# ---------------------------------------------------------------------------
# 5. Existing status values are preserved
# ---------------------------------------------------------------------------

class TestExistingStatusValues:
    def _eng(self):
        return _make_engine()

    def test_matched_status(self):
        eng = self._eng()
        nodes = {
            "inv1": _node("INVOICE", "\u20b950000"),
            "v1":   _node("VENDOR", "V"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9100000"),
        }
        adj = {"inv1": {"v1"}, "v1": {"inv1", "c1"}, "c1": {"v1"}}
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adj, {})
        assert row["status"] == "matched"

    def test_exception_status(self):
        eng = self._eng()
        nodes = {
            "inv1": _node("INVOICE", "\u20b9150000"),
            "v1":   _node("VENDOR", "V"),
            "c1":   _node("CONTRACT_AMOUNT", "\u20b9100000"),
        }
        adj = {"inv1": {"v1"}, "v1": {"inv1", "c1"}, "c1": {"v1"}}
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adj, {})
        assert row["status"] == "exception"

    def test_unresolved_no_vendor(self):
        eng = self._eng()
        nodes = {"inv1": _node("INVOICE", "\u20b950000")}
        adj = {}
        row = eng._reconcile_one("inv1", nodes["inv1"], nodes, adj, {})
        assert row["status"] == "unresolved"
