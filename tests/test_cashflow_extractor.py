"""
Unit tests for backend/compliance/cashflow_extractor.py

Covers
------
1. Healthy-mix workspace — invoices and settlements with dates produce a
   correct event list and a gapless daily aggregate.
2. Mostly-undated workspace — nodes without resolvable dates are skipped,
   the skip count is logged correctly, and the function still returns a
   (possibly short) series rather than raising.
3. aggregate_daily on an empty list — returns an empty DataFrame with the
   right columns, no exception.
4. aggregate_daily gap-filling — missing days in the middle of the range are
   filled with net_flow=0, n_events=0.
5. Direction classification — INVOICE_AMOUNT / CONTRACT_AMOUNT → outflow,
   SETTLEMENT_AMOUNT → inflow.
6. Date resolution priority — typed date-neighbour wins over date embedded
   in the node description.
7. No-amount nodes are silently skipped (not counted in skip_no_date).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(entity_type: str, description: str, source_id: str = "") -> dict:
    return {"entity_type": entity_type, "description": description, "source_id": source_id}


def _make_extractor() -> object:
    """Return a CashflowExtractor with the DB pool patched out."""
    with patch("backend.compliance.reconciliation_engine._get_pool"):
        from backend.compliance.cashflow_extractor import CashflowExtractor
        eng = CashflowExtractor.__new__(CashflowExtractor)
        eng.workspace_id = "ws-cashflow-test"
        eng.working_dir = "/tmp/fake"
        from backend.compliance.reconciliation_engine import ReconciliationEngine as _RE
        delegate = _RE.__new__(_RE)
        delegate.workspace_id = "ws-cashflow-test"
        delegate.working_dir = "/tmp/fake"
        eng._delegate = delegate
        return eng


def _run(coro):
    return asyncio.run(coro)


def _run_extract(nodes: dict, adjacency: dict) -> list[dict]:
    eng = _make_extractor()
    eng._delegate._load_nodes = AsyncMock(return_value=nodes)
    eng._delegate._load_adjacency = AsyncMock(return_value=adjacency)
    eng._delegate._load_text_chunks = MagicMock(return_value={})
    return _run(eng.extract())


# ---------------------------------------------------------------------------
# 1. Healthy-mix workspace
# ---------------------------------------------------------------------------

class TestHealthyMixWorkspace:
    """A workspace with invoices, contracts, and settlements all bearing dates."""

    def _build(self):
        nodes = {
            # --- outflows ---
            "inv_amt_1": _node("INVOICE_AMOUNT",    "\u20b950000 invoice Jan"),
            "due_1":     _node("DUE_DATE",          "Due 2024-01-10"),
            "inv_amt_2": _node("INVOICE_AMOUNT",    "\u20b975000 invoice Feb"),
            "due_2":     _node("DUE_DATE",          "Due 2024-02-15"),
            "con_amt_1": _node("CONTRACT_AMOUNT",   "\u20b9100000 contract March"),
            "due_3":     _node("DUE_DATE",          "2024-03-20"),
            # --- inflows ---
            "set_amt_1": _node("SETTLEMENT_AMOUNT", "\u20b960000 settlement A"),
            "sdate_1":   _node("SETTLEMENT_DATE",   "Settlement 2024-01-20"),
            "set_amt_2": _node("SETTLEMENT_AMOUNT", "\u20b980000 settlement B"),
            "sdate_2":   _node("SETTLEMENT_DATE",   "2024-02-28"),
            # --- irrelevant node (should be ignored) ---
            "vendor_1":  _node("VENDOR", "Some Vendor Co"),
        }
        adjacency = {
            "inv_amt_1": {"due_1"},
            "due_1":     {"inv_amt_1"},
            "inv_amt_2": {"due_2"},
            "due_2":     {"inv_amt_2"},
            "con_amt_1": {"due_3"},
            "due_3":     {"con_amt_1"},
            "set_amt_1": {"sdate_1"},
            "sdate_1":   {"set_amt_1"},
            "set_amt_2": {"sdate_2"},
            "sdate_2":   {"set_amt_2"},
        }
        return nodes, adjacency

    def test_event_count(self):
        rows = _run_extract(*self._build())
        assert len(rows) == 5, f"Expected 5 events, got {len(rows)}"

    def test_outflow_count(self):
        rows = _run_extract(*self._build())
        outflows = [r for r in rows if r["direction"] == "outflow"]
        assert len(outflows) == 3

    def test_inflow_count(self):
        rows = _run_extract(*self._build())
        inflows = [r for r in rows if r["direction"] == "inflow"]
        assert len(inflows) == 2

    def test_invoice_source_type(self):
        rows = _run_extract(*self._build())
        for r in rows:
            if r["node_id"] in ("inv_amt_1", "inv_amt_2", "con_amt_1"):
                assert r["source_type"] == "invoice", (
                    f"node {r['node_id']} should be source_type='invoice'"
                )

    def test_settlement_source_type(self):
        rows = _run_extract(*self._build())
        for r in rows:
            if r["node_id"] in ("set_amt_1", "set_amt_2"):
                assert r["source_type"] == "settlement", (
                    f"node {r['node_id']} should be source_type='settlement'"
                )

    def test_row_schema(self):
        rows = _run_extract(*self._build())
        for row in rows:
            for key in ("date", "amount", "direction", "source_type", "node_id"):
                assert key in row, f"Key '{key}' missing from row {row}"

    def test_date_format(self):
        rows = _run_extract(*self._build())
        for row in rows:
            # Must be a valid ISO date string
            d = date.fromisoformat(row["date"])
            assert isinstance(d, date)

    def test_amount_is_positive_float(self):
        rows = _run_extract(*self._build())
        for row in rows:
            assert isinstance(row["amount"], float)
            assert row["amount"] > 0

    def test_no_vendor_node_in_results(self):
        rows = _run_extract(*self._build())
        node_ids = {r["node_id"] for r in rows}
        assert "vendor_1" not in node_ids

    # --- aggregate_daily from the healthy series ---

    def test_aggregate_daily_columns(self):
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        assert list(df.columns) == ["date", "net_flow", "n_events"]

    def test_aggregate_daily_no_gaps(self):
        """Every calendar day between min and max date must appear."""
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        dates = list(df["date"])
        min_d, max_d = dates[0], dates[-1]
        expected_days = (max_d - min_d).days + 1
        assert len(df) == expected_days, (
            f"Expected {expected_days} rows (continuous), got {len(df)}"
        )

    def test_aggregate_daily_gap_days_have_zero_flow(self):
        """Gap-filled days must have net_flow=0 and n_events=0."""
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        gap_rows = df[df["n_events"] == 0]
        assert (gap_rows["net_flow"] == 0.0).all()

    def test_aggregate_daily_net_flow_sign(self):
        """Net flow on a day with only outflows must be negative."""
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        # 2024-01-10 has only inv_amt_1 (outflow 50000)
        jan10 = df[df["date"] == date(2024, 1, 10)]
        assert len(jan10) == 1
        assert jan10.iloc[0]["net_flow"] < 0

    def test_aggregate_daily_inflow_positive(self):
        """Net flow on a day with only inflows must be positive."""
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        # 2024-01-20 has only set_amt_1 (inflow 60000)
        jan20 = df[df["date"] == date(2024, 1, 20)]
        assert len(jan20) == 1
        assert jan20.iloc[0]["net_flow"] > 0

    def test_aggregate_daily_n_events_correct(self):
        """n_events must equal the number of cashflow nodes on that date."""
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        # Only one event on 2024-01-10
        assert df[df["date"] == date(2024, 1, 10)].iloc[0]["n_events"] == 1

    def test_aggregate_daily_n_events_dtype(self):
        """n_events must be an integer column, not float."""
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        assert df["n_events"].dtype == int


# ---------------------------------------------------------------------------
# 2. Mostly-undated workspace
# ---------------------------------------------------------------------------

class TestMostlyUndatedWorkspace:
    """Workspace where most cashflow nodes have no resolvable date."""

    def _build(self):
        nodes = {
            # Only this invoice has a resolvable date
            "inv_dated":   _node("INVOICE_AMOUNT",  "\u20b930000 2024-06-01"),
            # These have amounts but no date anywhere
            "inv_nodate1": _node("INVOICE_AMOUNT",  "\u20b940000 no-date invoice"),
            "inv_nodate2": _node("INVOICE_AMOUNT",  "\u20b955000 another undated"),
            "set_nodate":  _node("SETTLEMENT_AMOUNT", "\u20b910000 undated settlement"),
            # This has a date neighbour but NO parseable amount (no digits in description)
            "inv_noamt":   _node("INVOICE_AMOUNT",  "invoice reference only — no amount"),
            "due_noamt":   _node("DUE_DATE",        "2024-07-15"),
        }
        adjacency = {
            "inv_noamt": {"due_noamt"},
            "due_noamt": {"inv_noamt"},
        }
        return nodes, adjacency

    def test_returns_list_not_raises(self):
        """Must return a list, not raise an exception."""
        rows = _run_extract(*self._build())
        assert isinstance(rows, list)

    def test_only_dated_node_emitted(self):
        """Only the one node with a parseable date should appear in results."""
        rows = _run_extract(*self._build())
        # inv_dated has both an amount and a date in its description
        assert len(rows) == 1
        assert rows[0]["node_id"] == "inv_dated"

    def test_skip_count_logged(self, caplog):
        """The skip count for undated nodes must be logged at INFO level."""
        with caplog.at_level(logging.INFO, logger="backend.compliance.cashflow_extractor"):
            rows = _run_extract(*self._build())
        # 3 nodes have amounts but no date (inv_nodate1, inv_nodate2, set_nodate)
        assert "skipped_no_date=3" in caplog.text

    def test_correct_date_on_single_event(self):
        rows = _run_extract(*self._build())
        assert rows[0]["date"] == "2024-06-01"

    def test_aggregate_daily_on_short_series(self):
        """aggregate_daily must not raise even when given fewer than 20 events."""
        from backend.compliance.cashflow_extractor import aggregate_daily
        rows = _run_extract(*self._build())
        df = aggregate_daily(rows)
        # Single event — DataFrame has exactly one row (no gap-filling needed)
        assert len(df) == 1
        assert df.iloc[0]["net_flow"] < 0   # outflow


# ---------------------------------------------------------------------------
# 3. aggregate_daily — empty input
# ---------------------------------------------------------------------------

class TestAggregateDailyEmpty:
    def test_returns_dataframe(self):
        from backend.compliance.cashflow_extractor import aggregate_daily
        df = aggregate_daily([])
        assert isinstance(df, pd.DataFrame)

    def test_columns_present(self):
        from backend.compliance.cashflow_extractor import aggregate_daily
        df = aggregate_daily([])
        assert list(df.columns) == ["date", "net_flow", "n_events"]

    def test_no_rows(self):
        from backend.compliance.cashflow_extractor import aggregate_daily
        df = aggregate_daily([])
        assert len(df) == 0


# ---------------------------------------------------------------------------
# 4. aggregate_daily — gap filling
# ---------------------------------------------------------------------------

class TestAggregateDailyGapFill:
    """Events on day 1 and day 3 only — day 2 must be synthesised."""

    def _rows(self):
        return [
            {"date": "2024-05-01", "amount": 1000.0, "direction": "outflow",
             "source_type": "invoice",    "node_id": "n1"},
            {"date": "2024-05-03", "amount": 2000.0, "direction": "inflow",
             "source_type": "settlement", "node_id": "n2"},
        ]

    def test_three_rows_returned(self):
        from backend.compliance.cashflow_extractor import aggregate_daily
        df = aggregate_daily(self._rows())
        assert len(df) == 3

    def test_gap_day_is_zero(self):
        from backend.compliance.cashflow_extractor import aggregate_daily
        df = aggregate_daily(self._rows())
        gap = df[df["date"] == date(2024, 5, 2)]
        assert len(gap) == 1
        assert gap.iloc[0]["net_flow"] == 0.0
        assert gap.iloc[0]["n_events"] == 0

    def test_event_day_amounts(self):
        from backend.compliance.cashflow_extractor import aggregate_daily
        df = aggregate_daily(self._rows())
        day1 = df[df["date"] == date(2024, 5, 1)].iloc[0]
        day3 = df[df["date"] == date(2024, 5, 3)].iloc[0]
        assert day1["net_flow"] == -1000.0   # outflow
        assert day3["net_flow"] ==  2000.0   # inflow


# ---------------------------------------------------------------------------
# 5. Direction classification (unit test on _make_row)
# ---------------------------------------------------------------------------

class TestDirectionClassification:
    def _extractor(self):
        return _make_extractor()

    def test_invoice_amount_is_outflow(self):
        eng = self._extractor()
        node = _node("INVOICE_AMOUNT", "\u20b9999 2024-04-01")
        row = eng._make_row("n1", node, "INVOICE_AMOUNT", {"n1": node}, {})
        assert row is not None
        assert row["direction"] == "outflow"
        assert row["source_type"] == "invoice"

    def test_contract_amount_is_outflow(self):
        eng = self._extractor()
        node = _node("CONTRACT_AMOUNT", "\u20b9999 2024-04-01")
        row = eng._make_row("n1", node, "CONTRACT_AMOUNT", {"n1": node}, {})
        assert row is not None
        assert row["direction"] == "outflow"
        assert row["source_type"] == "invoice"

    def test_settlement_amount_is_inflow(self):
        eng = self._extractor()
        node = _node("SETTLEMENT_AMOUNT", "\u20b9999 2024-04-01")
        row = eng._make_row("n1", node, "SETTLEMENT_AMOUNT", {"n1": node}, {})
        assert row is not None
        assert row["direction"] == "inflow"
        assert row["source_type"] == "settlement"


# ---------------------------------------------------------------------------
# 6. Date resolution priority — typed neighbour wins over inline date
# ---------------------------------------------------------------------------

class TestDateResolutionPriority:
    def test_neighbour_date_takes_precedence(self):
        """DUE_DATE neighbour (2024-09-01) must beat the inline date (2024-01-01)."""
        eng = _make_extractor()
        nodes = {
            "inv1": _node("INVOICE_AMOUNT", "\u20b9500 2024-01-01"),
            "due1": _node("DUE_DATE",       "Due date: 2024-09-01"),
        }
        adjacency = {"inv1": {"due1"}, "due1": {"inv1"}}
        row = eng._make_row("inv1", nodes["inv1"], "INVOICE_AMOUNT", nodes, adjacency)
        assert row is not None
        assert row["date"] == "2024-09-01"

    def test_fallback_to_inline_date_when_no_neighbour(self):
        """When no DUE_DATE neighbour exists, inline date must be used."""
        eng = _make_extractor()
        nodes = {"inv1": _node("INVOICE_AMOUNT", "\u20b9500 2024-03-15")}
        row = eng._make_row("inv1", nodes["inv1"], "INVOICE_AMOUNT", nodes, {})
        assert row is not None
        assert row["date"] == "2024-03-15"


# ---------------------------------------------------------------------------
# 7. No-amount nodes skipped (not counted as skipped_no_date)
# ---------------------------------------------------------------------------

class TestNoAmountSkip:
    def test_no_amount_node_not_in_results(self):
        nodes = {
            # Description contains no digits — _parse_amount returns None
            "no_amt": _node("INVOICE_AMOUNT", "invoice reference only — no amount here"),
            "due1":   _node("DUE_DATE",       "2024-08-01"),
        }
        adjacency = {"no_amt": {"due1"}, "due1": {"no_amt"}}
        rows = _run_extract(nodes, adjacency)
        assert len(rows) == 0

    def test_no_amount_does_not_inflate_no_date_count(self, caplog):
        """skipped_no_date must be 0 when the only skip is due to missing amount."""
        nodes = {
            # Description contains no digits — _parse_amount returns None
            "no_amt": _node("INVOICE_AMOUNT", "invoice reference only — no amount here"),
            "due1":   _node("DUE_DATE",       "2024-08-01"),
        }
        adjacency = {"no_amt": {"due1"}, "due1": {"no_amt"}}
        with caplog.at_level(logging.INFO, logger="backend.compliance.cashflow_extractor"):
            _run_extract(nodes, adjacency)
        assert "skipped_no_date=0" in caplog.text
