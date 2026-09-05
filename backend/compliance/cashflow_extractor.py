"""
Cashflow Extractor

Enterprise Compliance Intelligence Platform

Purpose
-------
Turn a workspace's existing knowledge graph into a clean daily net-cash-flow
time series.  No model, no training — pure graph traversal + regex, same as
reconciliation_engine.py and tax_matcher.py.

Approach
--------
For every INVOICE_AMOUNT, CONTRACT_AMOUNT, and SETTLEMENT_AMOUNT node in the
workspace the extractor:

  1. Parses the monetary amount from the node description via _parse_amount
     (imported from reconciliation_engine — not reimplemented here).
  2. Resolves the best available date (DUE_DATE neighbour for
     INVOICE_AMOUNT/CONTRACT_AMOUNT, SETTLEMENT_DATE neighbour for
     SETTLEMENT_AMOUNT) via _parse_date (also imported).
  3. Emits one row per datable event:

       {
         "date":        "YYYY-MM-DD",
         "amount":      float,
         "direction":   "outflow" | "inflow",
         "source_type": "invoice" | "settlement",
         "node_id":     str,
       }

     INVOICE_AMOUNT / CONTRACT_AMOUNT  → outflow  (money owed out)
     SETTLEMENT_AMOUNT                 → inflow   (money received)

  4. Skips (never guesses) any node whose date cannot be resolved, and logs a
     summary count so missing dates are measurable, not silent.

Delegation pattern
------------------
All DB/filesystem access is delegated to a ReconciliationEngine instance
created via __new__ (same pattern as TaxMatcher).  _parse_amount, _parse_date,
and _norm_type are imported directly — no reimplementation.

The rupee symbol is written as \\u20b9 throughout (see reconciliation_engine
module docstring for the reason).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from backend.compliance.reconciliation_engine import ReconciliationEngine as _RE
from backend.compliance.reconciliation_engine import _norm_type, _parse_amount, _parse_date

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node-type constants
# ---------------------------------------------------------------------------

_OUTFLOW_TYPES = {"INVOICE_AMOUNT", "CONTRACT_AMOUNT"}
_INFLOW_TYPES  = {"SETTLEMENT_AMOUNT"}
_CASHFLOW_TYPES = _OUTFLOW_TYPES | _INFLOW_TYPES

# Date-bearing neighbour types per cashflow node type.
# We look for these neighbour types in order; the first parseable date wins.
_DATE_NEIGHBOUR_TYPES: dict[str, list[str]] = {
    "INVOICE_AMOUNT":  ["DUE_DATE", "INVOICE_DATE", "DATE"],
    "CONTRACT_AMOUNT": ["DUE_DATE", "CONTRACT_DATE", "DATE"],
    "SETTLEMENT_AMOUNT": ["SETTLEMENT_DATE", "PAYMENT_DATE", "DATE"],
}


# ---------------------------------------------------------------------------
# Module-level convenience wrapper (matches the public contract requested)
# ---------------------------------------------------------------------------

async def extract_cashflow_series(workspace_id: str, working_dir: str) -> list[dict]:
    """Return a list of cashflow event rows for *workspace_id*.

    Each row has the shape::

        {
            "date":        "YYYY-MM-DD",   # str
            "amount":      float,
            "direction":   "outflow" | "inflow",
            "source_type": "invoice" | "settlement",
            "node_id":     str,
        }

    Nodes with no resolvable date are skipped; the skip count is logged at
    INFO level so it is visible in server logs and measurable in dashboards.
    """
    extractor = CashflowExtractor(workspace_id=workspace_id, working_dir=working_dir)
    return await extractor.extract()


def aggregate_daily(rows: list[dict]) -> pd.DataFrame:
    """Aggregate per-event rows into a continuous daily time series.

    Parameters
    ----------
    rows:
        The list returned by ``extract_cashflow_series`` / ``CashflowExtractor.extract``.

    Returns
    -------
    pandas.DataFrame with columns:

        date       — calendar day (``datetime.date``)
        net_flow   — algebraic sum of amounts (inflows positive, outflows negative)
        n_events   — count of events on that day

    The returned frame covers **every calendar day** between the earliest and
    latest dated event (inclusive).  Days with no events are filled with
    ``net_flow=0`` and ``n_events=0`` so callers receive a continuous series
    without holes.  If *rows* is empty, an empty DataFrame with those three
    columns is returned.

    Threshold decisions (e.g. "too few events to forecast") belong in the model
    step — this function always returns whatever data it has.
    """
    if not rows:
        return pd.DataFrame(columns=["date", "net_flow", "n_events"])

    # Build a signed-amount series: inflow = +amount, outflow = -amount.
    records = []
    for row in rows:
        sign = 1.0 if row["direction"] == "inflow" else -1.0
        records.append(
            {
                "date":     row["date"],           # "YYYY-MM-DD" str
                "signed":   sign * float(row["amount"]),
                "n_events": 1,
            }
        )

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"]).dt.date  # keep as Python date

    # Aggregate: one row per calendar day.
    daily = (
        df.groupby("date")
        .agg(net_flow=("signed", "sum"), n_events=("n_events", "sum"))
        .reset_index()
    )

    # Fill the contiguous date range — forecasters need no gaps.
    min_date: date = daily["date"].min()
    max_date: date = daily["date"].max()
    all_dates = pd.DataFrame(
        {"date": [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]}
    )

    result = (
        all_dates.merge(daily, on="date", how="left")
        .fillna({"net_flow": 0.0, "n_events": 0})
        .astype({"n_events": int})
        .sort_values("date")
        .reset_index(drop=True)
    )
    return result


# ---------------------------------------------------------------------------
# CashflowExtractor class
# ---------------------------------------------------------------------------

class CashflowExtractor:
    """Extract a cashflow time series from the knowledge graph of one workspace.

    Parameters
    ----------
    workspace_id:
        CockroachDB workspace scope (equals case_id in this app).
    working_dir:
        Filesystem directory holding ``kv_store_text_chunks.json`` for this
        workspace (only used to resolve source files — not required for the
        core extraction).
    """

    def __init__(self, workspace_id: str, working_dir: str):
        if not workspace_id:
            raise ValueError("CashflowExtractor requires workspace_id")
        self.workspace_id = workspace_id
        self.working_dir = working_dir
        # Delegate all DB / filesystem access to ReconciliationEngine — same
        # pattern as TaxMatcher.  We bypass __init__ to avoid re-running its
        # validation; workspace_id and working_dir are set manually.
        self._delegate = _RE.__new__(_RE)
        self._delegate.workspace_id = workspace_id
        self._delegate.working_dir = working_dir

    # ------------------------------------------------------------------
    # Neighbour resolution
    # ------------------------------------------------------------------

    def _find_neighbor_of_type(
        self,
        node_id: str,
        wanted_type: str,
        nodes: dict,
        adjacency: dict[str, set[str]],
    ) -> str | None:
        """Return the first lexicographically-sorted neighbour whose normalised
        entity_type matches *wanted_type*, or ``None`` if none found.

        Deterministic sort mirrors the pattern in ReconciliationEngine and
        TaxMatcher.
        """
        candidates = sorted(
            nid
            for nid in adjacency.get(node_id, ())
            if nodes.get(nid) and _norm_type(nodes[nid].get("entity_type")) == wanted_type
        )
        return candidates[0] if candidates else None

    # ------------------------------------------------------------------
    # Date resolution
    # ------------------------------------------------------------------

    def _resolve_date(
        self,
        node_id: str,
        node: dict,
        norm_type: str,
        nodes: dict,
        adjacency: dict[str, set[str]],
    ) -> date | None:
        """Resolve the best available date for a cashflow node.

        Strategy (in order of preference):

        1. Look for a typed date-neighbour (DUE_DATE, SETTLEMENT_DATE, etc.)
           and parse its description.
        2. If no suitable neighbour exists, fall back to parsing a date
           directly from the node's own description (e.g. "Invoice 2024-03-15
           \u20b950,000").

        Returns ``None`` when no parseable date is found anywhere.
        """
        # Step 1 — look for typed date-neighbour nodes.
        for date_type in _DATE_NEIGHBOUR_TYPES.get(norm_type, []):
            neighbour_id = self._find_neighbor_of_type(node_id, date_type, nodes, adjacency)
            if neighbour_id is None:
                continue
            d = _parse_date(nodes[neighbour_id].get("description"))
            if d is not None:
                return d

        # Step 2 — fallback: parse date from the node's own description.
        return _parse_date(node.get("description"))

    # ------------------------------------------------------------------
    # Per-node event construction
    # ------------------------------------------------------------------

    def _make_row(
        self,
        node_id: str,
        node: dict,
        norm_type: str,
        nodes: dict,
        adjacency: dict[str, set[str]],
    ) -> dict | None:
        """Return one event row dict, or ``None`` if the node should be skipped.

        A node is skipped when either:
        - its description cannot yield a parseable amount, or
        - no resolvable date is found (either via neighbours or its own description).

        Skips are counted by the caller — they are never silent.
        """
        amount = _parse_amount(node.get("description"))
        if amount is None:
            return None  # no usable amount — skip

        d = self._resolve_date(node_id, node, norm_type, nodes, adjacency)
        if d is None:
            return None  # no resolvable date — skip (counted by caller)

        direction: str
        source_type: str
        if norm_type in _OUTFLOW_TYPES:
            direction   = "outflow"
            source_type = "invoice"
        else:
            direction   = "inflow"
            source_type = "settlement"

        return {
            "date":        d.isoformat(),   # "YYYY-MM-DD"
            "amount":      amount,
            "direction":   direction,
            "source_type": source_type,
            "node_id":     node_id,
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def extract(self) -> list[dict]:
        """Extract cashflow events for the whole workspace.

        Returns a list of event dicts (see module docstring for the shape).
        Nodes with no resolvable date are skipped; a summary count is logged at
        INFO level so the skip rate is measurable without being noisy.
        """
        nodes     = await self._delegate._load_nodes()
        adjacency = await self._delegate._load_adjacency()

        rows: list[dict] = []
        skipped_no_date   = 0
        skipped_no_amount = 0

        for node_id, node in nodes.items():
            norm_type = _norm_type(node.get("entity_type"))
            if norm_type not in _CASHFLOW_TYPES:
                continue

            amount = _parse_amount(node.get("description"))
            if amount is None:
                skipped_no_amount += 1
                continue

            d = self._resolve_date(node_id, node, norm_type, nodes, adjacency)
            if d is None:
                skipped_no_date += 1
                continue

            row = self._make_row(node_id, node, norm_type, nodes, adjacency)
            if row is not None:
                rows.append(row)

        logger.info(
            "CashflowExtractor workspace=%s  events=%d  skipped_no_date=%d  "
            "skipped_no_amount=%d",
            self.workspace_id,
            len(rows),
            skipped_no_date,
            skipped_no_amount,
        )

        return rows
