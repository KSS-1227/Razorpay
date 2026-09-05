"""
Tax-Line Matcher

Enterprise Compliance Intelligence Platform

Purpose
-------
For each TAX_LINE_ITEM in a workspace's knowledge graph, resolve its HSN_CODE
neighbor, then that HSN_CODE's expected TAX_RATE neighbor (from an ingested
GST rate-schedule reference document), and compare against the TAX_RATE
actually applied on the line item itself.

Design notes
------------
- Pure graph traversal + regex. No LLM calls.
- Shared helpers (_norm_type, _parse_amount, _get_pool, node/adjacency loaders,
  _source_files) are imported directly from reconciliation_engine — no logic is
  duplicated.
- Deterministic neighbor selection: candidates sorted lexicographically, same
  fix already applied in ReconciliationEngine.
- The rupee symbol is written as \\u20b9 throughout (see reconciliation_engine
  module docstring for the reason).

Graph shape assumed
-------------------
    TAX_LINE_ITEM ---edge--- HSN_CODE ---edge--- TAX_RATE (expected, from rate schedule)

The applied rate is always parsed from the TAX_LINE_ITEM node's own description
(e.g. "Consulting services: \u20b940,000 @ 18%"). The HSN_CODE's TAX_RATE
neighbor supplies the expected rate from an ingested rate-schedule document.

Result statuses
---------------
- "matched":    applied rate == expected rate
- "exception":  applied rate != expected rate (both rates in reason string)
- "unresolved": missing HSN link, missing rate-schedule entry, or unparseable
                rate — never dropped silently
"""
from __future__ import annotations

import re

from backend.compliance.reconciliation_engine import ReconciliationEngine as _RE
from backend.compliance.reconciliation_engine import _norm_type

# Matches a percentage rate, e.g. "18%", "GST @ 18%", "5.0%", "0.1%"
_RATE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')


def _parse_rate(description: str | None) -> float | None:
    """Extract the first percentage value from a node description.

    Returns the numeric value (e.g. 18.0 for "18%"), or None if not found.
    """
    if not description:
        return None
    m = _RATE_RE.search(description)
    return float(m.group(1)) if m else None


class TaxMatcher:
    """Match applied tax rates against expected rates for a single workspace.

    Parameters
    ----------
    workspace_id:
        CockroachDB workspace scope (equals case_id in this app).
    working_dir:
        Filesystem directory holding ``kv_store_text_chunks.json`` for this
        workspace (used only to resolve ``source_files``).
    """

    def __init__(self, workspace_id: str, working_dir: str):
        if not workspace_id:
            raise ValueError("TaxMatcher requires workspace_id")
        self.workspace_id = workspace_id
        self.working_dir = working_dir
        # Delegate DB/filesystem loading to a ReconciliationEngine instance —
        # its _pool, _load_nodes, _load_adjacency, _load_text_chunks, and
        # _source_files methods are identical to what we need.
        self._delegate = _RE.__new__(_RE)
        self._delegate.workspace_id = workspace_id
        self._delegate.working_dir = working_dir

    # ------------------------------------------------------------------
    # Neighbor resolution (same deterministic pattern as ReconciliationEngine)
    # ------------------------------------------------------------------

    def _find_neighbor_of_type(
        self,
        node_id: str,
        wanted_type: str,
        nodes: dict,
        adjacency: dict[str, set[str]],
    ) -> tuple[str | None, str | None]:
        """Return ``(neighbor_id, ambiguity_reason)`` — deterministic, sorted.

        Mirrors ReconciliationEngine._find_neighbor_of_type exactly.
        """
        candidates = sorted(
            nid for nid in adjacency.get(node_id, ())
            if nodes.get(nid) and _norm_type(nodes[nid].get("entity_type")) == wanted_type
        )
        if not candidates:
            return None, None
        chosen = candidates[0]
        ambiguity = (
            f"Multiple {wanted_type} nodes found — used {chosen}"
            if len(candidates) > 1
            else None
        )
        return chosen, ambiguity

    # ------------------------------------------------------------------
    # Per-item matching
    # ------------------------------------------------------------------

    def _match_one(
        self,
        item_id: str,
        item: dict,
        nodes: dict,
        adjacency: dict[str, set[str]],
        text_chunks: dict,
    ) -> dict:
        """Produce a single result row for one TAX_LINE_ITEM node."""
        status: str
        reason: str | None = None
        applied_rate: float | None = None
        expected_rate: float | None = None
        hsn_id: str | None = None

        # Step 1: applied rate — always parsed from the line item's own description.
        # A neighboring TAX_RATE node represents the *expected* schedule rate, not
        # the applied rate, so we must not read it here.
        applied_rate = _parse_rate(item.get("description"))

        if applied_rate is None:
            return self._unresolved(
                item_id, item, hsn_id, applied_rate, expected_rate,
                "Could not parse applied tax rate from line item description",
                text_chunks,
            )

        # Step 2: HSN_CODE neighbor of the line item
        hsn_id, hsn_ambiguity = self._find_neighbor_of_type(
            item_id, "HSN_CODE", nodes, adjacency
        )
        if hsn_id is None:
            return self._unresolved(
                item_id, item, hsn_id, applied_rate, expected_rate,
                "No HSN_CODE node linked to this tax line item",
                text_chunks,
            )

        # Step 3: expected TAX_RATE from the HSN_CODE's neighbor (rate schedule)
        expected_rate_id, expected_ambiguity = self._find_neighbor_of_type(
            hsn_id, "TAX_RATE", nodes, adjacency
        )
        if expected_rate_id is None:
            return self._unresolved(
                item_id, item, hsn_id, applied_rate, expected_rate,
                f"No expected TAX_RATE found for HSN_CODE {hsn_id}",
                text_chunks,
            )

        expected_rate = _parse_rate(nodes[expected_rate_id].get("description"))
        if expected_rate is None:
            return self._unresolved(
                item_id, item, hsn_id, applied_rate, expected_rate,
                f"Could not parse expected rate from TAX_RATE node {expected_rate_id}",
                text_chunks,
            )

        # Collect any ambiguity notes
        notes = [n for n in (hsn_ambiguity, expected_ambiguity) if n]
        reason = "; ".join(notes) if notes else None

        if applied_rate == expected_rate:
            status = "matched"
        else:
            status = "exception"
            mismatch = (
                f"Applied rate {applied_rate}% does not match "
                f"expected rate {expected_rate}% for HSN {hsn_id}"
            )
            reason = f"{mismatch}; {reason}" if reason else mismatch

        return {
            "item_id":       item_id,
            "hsn_id":        hsn_id,
            "status":        status,
            "reason":        reason,
            "applied_rate":  applied_rate,
            "expected_rate": expected_rate,
            "source_files":  self._delegate._source_files(item, text_chunks),
        }

    def _unresolved(
        self,
        item_id: str,
        item: dict,
        hsn_id: str | None,
        applied_rate: float | None,
        expected_rate: float | None,
        reason: str,
        text_chunks: dict,
    ) -> dict:
        return {
            "item_id":       item_id,
            "hsn_id":        hsn_id,
            "status":        "unresolved",
            "reason":        reason,
            "applied_rate":  applied_rate,
            "expected_rate": expected_rate,
            "source_files":  self._delegate._source_files(item, text_chunks),
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def match(self) -> dict:
        """Run tax-rate matching for the whole workspace and return the summary dict."""
        nodes     = await self._delegate._load_nodes()
        adjacency = await self._delegate._load_adjacency()
        text_chunks = self._delegate._load_text_chunks()

        tax_items = {
            nid: nd for nid, nd in nodes.items()
            if _norm_type(nd.get("entity_type")) == "TAX_LINE_ITEM"
        }

        results: list[dict] = []
        counts = {"matched": 0, "exception": 0, "unresolved": 0}

        for item_id, item in tax_items.items():
            row = self._match_one(item_id, item, nodes, adjacency, text_chunks)
            results.append(row)
            counts[row["status"]] = counts.get(row["status"], 0) + 1

        total = len(tax_items)
        match_rate = f"{round((counts['matched'] / total) * 100)}%" if total else "0%"

        return {
            "total":       total,
            "matched":     counts["matched"],
            "exceptions":  counts["exception"],
            "unresolved":  counts["unresolved"],
            "match_rate":  match_rate,
            "results":     results,
        }
