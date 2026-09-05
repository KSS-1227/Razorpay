"""
Reconciliation Engine

Enterprise Compliance Intelligence Platform

Purpose
-------
Reconcile every INVOICE entity in a workspace's knowledge graph against the
CONTRACT_AMOUNT entity of the VENDOR it is linked to, flagging amount
mismatches and approval-limit violations.

Design notes
------------
- Pure graph traversal + regex. No LLM calls, so this is fast and deterministic.
- Graph nodes/edges are read from CockroachDB (workspace-scoped rows), reusing
  the existing async connection pool from ``backend.cockroach_graph_storage``.
- ``source_files`` are resolved from the local ``kv_store_text_chunks.json`` KV
  store in the workspace ``working`` directory (same store the pipeline writes).
- The rupee symbol is written as ``\u20b9`` throughout so this file stays pure
  ASCII on disk (avoids a cp1252 decode error when the file is read back with a
  plain ``open().read()`` on Windows).

Graph shape assumed
-------------------
    INVOICE ---edge--- VENDOR ---edge--- CONTRACT_AMOUNT
Any invoice that does not fit this shape is reported as ``unresolved`` with a
reason, never dropped silently.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

# Reuse the shared async pool — do NOT open a second connection to CockroachDB.
from backend.cockroach_graph_storage import _get_pool

# Matches an optional currency symbol (rupee / dollar) followed by an
# Indian- or Western-formatted number, e.g. "\u20b980,000", "$5,200", "1,00,000".
# The rupee symbol is written as \u20b9 (see module docstring).
_AMOUNT_RE = re.compile(r'[' '\u20b9' r'\$]?\s*[\d,]+(?:\.\d+)?')

# Multi-value separator used across the graph pipeline (see backend/core/prompt.py).
_SEP = "<SEP>"

_INVOICE_TYPES = {"INVOICE", "INVOICE_AMOUNT"}
_CONTRACT_TYPES = {"CONTRACT_AMOUNT", "PAYMENT_TERMS"}

# ISO date patterns found in node descriptions, e.g. "2024-03-15" or "15/03/2024".
_DATE_RE = re.compile(
    r'\b(\d{4}-\d{2}-\d{2})\b'          # YYYY-MM-DD
    r'|'
    r'\b(\d{2}/\d{2}/\d{4})\b'          # DD/MM/YYYY
)


def _norm_type(entity_type: str | None) -> str:
    """Normalize an entity_type for comparison: strip stray quotes/whitespace, upper-case.

    Graph nodes sometimes carry the type wrapped in literal quotes (e.g. '"INVOICE"')
    — the rest of the codebase does the same ``.replace('"', "")`` cleanup.
    """
    return (entity_type or "").replace('"', "").strip().upper()


def _parse_amount(description: str | None) -> float | None:
    """Extract a numeric amount from a node description.

    Prefers the first match that carries a currency symbol (so an invoice number
    like ``INV-2024-047`` is not mistaken for the amount ``2024``), then falls
    back to the first bare number. Handles Indian comma grouping ("1,00,000").
    Returns ``None`` when nothing parseable is found.
    """
    if not description:
        return None

    fallback: float | None = None
    for token in _AMOUNT_RE.findall(description):
        cleaned = re.sub(r"[^\d.]", "", token)
        if not cleaned or cleaned == ".":
            continue
        try:
            value = float(cleaned)
        except ValueError:
            continue
        if "\u20b9" in token or "$" in token:
            return value  # a currency-tagged amount wins outright
        if fallback is None:
            fallback = value  # remember the first bare number as a fallback
    return fallback


def _parse_date(description: str | None) -> date | None:
    """Extract the first parseable date from a node description. Returns None if none found."""
    if not description:
        return None
    for m in _DATE_RE.finditer(description):
        iso, dmy = m.group(1), m.group(2)
        try:
            if iso:
                return datetime.strptime(iso, "%Y-%m-%d").date()
            if dmy:
                return datetime.strptime(dmy, "%d/%m/%Y").date()
        except ValueError:
            continue
    return None


def _iso_week(d: date) -> tuple[int, int]:
    """Return (ISO year, ISO week number) for a date."""
    return d.isocalendar()[:2]


def _fmt(amount: float) -> str:
    """Render an amount without a trailing ``.0`` for whole numbers."""
    return f"{amount:g}"


class ReconciliationEngine:
    """Reconcile invoices against vendor contracts for a single workspace.

    Parameters
    ----------
    workspace_id:
        CockroachDB workspace scope. In this app it equals the case_id
        (see WorkspaceDocumentService, which passes workspace_id=case_id).
    working_dir:
        Filesystem directory holding ``kv_store_text_chunks.json`` for this
        workspace (used only to resolve ``source_files``).
    """

    def __init__(self, workspace_id: str, working_dir: str):
        if not workspace_id:
            raise ValueError("ReconciliationEngine requires workspace_id")
        self.workspace_id = workspace_id
        self.working_dir = working_dir

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    async def _pool(self):
        pool = _get_pool()
        if pool.closed:  # psycopg_pool is created with open=False
            await pool.open()
        return pool

    async def _load_nodes(self) -> dict[str, dict]:
        """Return ``{node_id: {entity_type, description, source_id}}`` for the workspace."""
        pool = await self._pool()
        async with pool.connection() as conn:
            rows = await (await conn.execute(
                "SELECT node_id, entity_type, description, source_id "
                "FROM graph_nodes WHERE workspace_id=%s",
                (self.workspace_id,),
            )).fetchall()
        return {
            row[0]: {
                "entity_type": row[1],
                "description": row[2],
                "source_id": row[3],
            }
            for row in rows
        }

    async def _load_adjacency(self) -> dict[str, set[str]]:
        """Return an undirected adjacency map ``{node_id: {neighbor_id, ...}}``."""
        pool = await self._pool()
        async with pool.connection() as conn:
            rows = await (await conn.execute(
                "SELECT source_id, target_id FROM graph_edges WHERE workspace_id=%s",
                (self.workspace_id,),
            )).fetchall()
        adjacency: dict[str, set[str]] = {}
        for source_id, target_id in rows:
            adjacency.setdefault(source_id, set()).add(target_id)
            adjacency.setdefault(target_id, set()).add(source_id)
        return adjacency

    def _load_text_chunks(self) -> dict:
        """Load ``kv_store_text_chunks.json`` from the working dir (empty dict if absent)."""
        path = Path(self.working_dir) / "kv_store_text_chunks.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}

    def _source_files(self, node: dict, text_chunks: dict) -> list[str]:
        """Resolve a node's ``source_id`` chunk list to unique source file names."""
        files: set[str] = set()
        for raw_sid in (node.get("source_id") or "").split(_SEP):
            sid = raw_sid.strip()
            if not sid:
                continue
            chunk = text_chunks.get(sid)
            if chunk:
                files.add(chunk.get("file_name", "unknown"))
        return sorted(files)

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    def _find_neighbor_of_type(
        self,
        node_id: str,
        wanted_type: str,
        nodes: dict,
        adjacency: dict[str, set[str]],
    ) -> tuple[str | None, str | None]:
        """Return ``(neighbor_id, ambiguity_reason)`` for the first neighbor whose
        normalized entity_type == wanted_type.

        When multiple matches exist, candidates are sorted lexicographically by
        node_id for reproducibility; the first is returned and ``ambiguity_reason``
        is set to a human-readable note. Returns ``(None, None)`` when no match.
        """
        candidates = sorted(
            nid for nid in adjacency.get(node_id, ())
            if nodes.get(nid) and _norm_type(nodes[nid].get("entity_type")) == wanted_type
        )
        if not candidates:
            return None, None
        chosen = candidates[0]
        ambiguity = (
            f"Multiple {wanted_type} nodes found for vendor — used {chosen}"
            if len(candidates) > 1
            else None
        )
        return chosen, ambiguity

    def _reconcile_one(
        self,
        invoice_id: str,
        invoice: dict,
        nodes: dict,
        adjacency: dict[str, set[str]],
        text_chunks: dict,
    ) -> dict:
        """Reconcile a single invoice node into a result row."""
        invoice_amount = _parse_amount(invoice.get("description"))
        contract_amount: float | None = None
        status: str
        reason: str | None = None
        vendor_id: str | None = None

        if invoice_amount is None:
            status, reason = "unresolved", "Could not parse amount from document"
        else:
            vendor_id, _ = self._find_neighbor_of_type(invoice_id, "VENDOR", nodes, adjacency)
            if vendor_id is None:
                status, reason = "unresolved", "Invoice not linked to any vendor"
            else:
                contract_id, ambiguity = self._find_neighbor_of_type(
                    vendor_id, "CONTRACT_AMOUNT", nodes, adjacency
                )
                if contract_id is None:
                    status, reason = "unresolved", "No matching vendor contract found"
                else:
                    if ambiguity:
                        reason = ambiguity
                    contract_amount = _parse_amount(nodes[contract_id].get("description"))
                    if contract_amount is None:
                        status = "unresolved"
                        reason = "Could not parse amount from document"
                    elif invoice_amount <= contract_amount:
                        status = "matched"
                    else:
                        status = "exception"
                        reason = (
                            f"Invoice amount {_fmt(invoice_amount)} exceeds "
                            f"contract limit {_fmt(contract_amount)}"
                        )

        # Per-vendor approval limit: resolve through this invoice's own vendor.
        approval_threshold: float | None = None
        if vendor_id is not None:
            approval_id, _ = self._find_neighbor_of_type(
                vendor_id, "APPROVAL_LIMIT", nodes, adjacency
            )
            if approval_id is not None:
                approval_threshold = _parse_amount(nodes[approval_id].get("description"))

        requires_approval = (
            invoice_amount is not None
            and approval_threshold is not None
            and invoice_amount > approval_threshold
        )

        return {
            "invoice_id": invoice_id,
            "vendor_id": vendor_id,
            "status": status,
            "reason": reason,
            "invoice_amount": invoice_amount,
            "contract_amount": contract_amount,
            "requires_approval": requires_approval,
            "flags": [],
            "source_files": self._source_files(invoice, text_chunks),
        }

    async def reconcile(self) -> dict:
        """Run reconciliation for the whole workspace and return the summary dict."""
        nodes = await self._load_nodes()
        adjacency = await self._load_adjacency()
        text_chunks = self._load_text_chunks()

        invoices = {
            nid: nd for nid, nd in nodes.items()
            if _norm_type(nd.get("entity_type")) in _INVOICE_TYPES
        }
        # Built per the spec; PAYMENT_TERMS is grouped with contracts even though
        # only CONTRACT_AMOUNT is used for the numeric comparison below.
        contracts = {  # noqa: F841 - kept for parity with the spec's Step 1
            nid: nd for nid, nd in nodes.items()
            if _norm_type(nd.get("entity_type")) in _CONTRACT_TYPES
        }

        results: list[dict] = []
        counts = {"matched": 0, "exception": 0, "unresolved": 0}
        for invoice_id, invoice in invoices.items():
            row = self._reconcile_one(
                invoice_id, invoice, nodes, adjacency, text_chunks
            )
            results.append(row)
            counts[row["status"]] = counts.get(row["status"], 0) + 1

        # Second pass: structuring check (fix 2).
        # Group by (vendor_id, calendar week of invoice date if parseable).
        # Key: (vendor_id, week_key) where week_key is an ISO (year, week) tuple or None.
        from collections import defaultdict
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for row in results:
            vid = row.get("vendor_id")
            if vid is None or row["invoice_amount"] is None:
                continue
            inv_node = invoices.get(row["invoice_id"])
            inv_date = _parse_date(inv_node.get("description") if inv_node else None)
            if inv_date is not None:
                week_key: object = _iso_week(inv_date)
            else:
                # Undated invoices must never be grouped together — each gets its
                # own singleton key so unrelated invoices cannot trigger a false
                # structuring flag.
                week_key = ("undated", row["invoice_id"])
            groups[(vid, week_key)].append(row)

        structuring_groups = 0
        for (vid, _week), group_rows in groups.items():
            # Resolve this vendor's approval limit once per group.
            approval_id, _ = self._find_neighbor_of_type(
                vid, "APPROVAL_LIMIT", nodes, adjacency
            )
            if approval_id is None:
                continue
            limit = _parse_amount(nodes[approval_id].get("description"))
            if limit is None:
                continue
            group_sum = sum(r["invoice_amount"] for r in group_rows)
            # All individual invoices must be under the limit for structuring to apply.
            if group_sum > limit and all(r["invoice_amount"] <= limit for r in group_rows):
                structuring_groups += 1
                for r in group_rows:
                    r["flags"].append("possible_structuring")

        total = len(invoices)
        match_rate = f"{round((counts['matched'] / total) * 100)}%" if total else "0%"

        return {
            "total": total,
            "matched": counts["matched"],
            "exceptions": counts["exception"],
            "unresolved": counts["unresolved"],
            "match_rate": match_rate,
            "structuring_groups": structuring_groups,
            "results": results,
        }
