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
- The rupee symbol is written as ``\\u20b9`` throughout so this file stays pure
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
from pathlib import Path

# Reuse the shared async pool — do NOT open a second connection to CockroachDB.
from backend.cockroach_graph_storage import _get_pool

# Matches an optional currency symbol (rupee / dollar) followed by an
# Indian- or Western-formatted number, e.g. "₹80,000", "$5,200", "1,00,000".
# The rupee symbol is injected via a non-raw literal ('₹') concatenated
# with the raw parts, because raw strings do not process \u escapes.
_AMOUNT_RE = re.compile(r'[' '₹' r'\$]?\s*[\d,]+(?:\.\d+)?')

# Multi-value separator used across the graph pipeline (see backend/core/prompt.py).
_SEP = "<SEP>"

_INVOICE_TYPES = {"INVOICE", "INVOICE_AMOUNT"}
_CONTRACT_TYPES = {"CONTRACT_AMOUNT", "PAYMENT_TERMS"}


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
        if "₹" in token or "$" in token:
            return value  # a currency-tagged amount wins outright
        if fallback is None:
            fallback = value  # remember the first bare number as a fallback
    return fallback


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
    ) -> str | None:
        """Return a neighbor of ``node_id`` whose normalized entity_type == wanted_type."""
        for neighbor_id in adjacency.get(node_id, ()):  # deterministic-enough for a set
            neighbor = nodes.get(neighbor_id)
            if neighbor and _norm_type(neighbor.get("entity_type")) == wanted_type:
                return neighbor_id
        return None

    def _reconcile_one(
        self,
        invoice_id: str,
        invoice: dict,
        nodes: dict,
        adjacency: dict[str, set[str]],
        approval_threshold: float | None,
        text_chunks: dict,
    ) -> dict:
        """Reconcile a single invoice node into a result row."""
        invoice_amount = _parse_amount(invoice.get("description"))
        contract_amount: float | None = None
        status: str
        reason: str | None = None

        if invoice_amount is None:
            status, reason = "unresolved", "Could not parse amount from document"
        else:
            vendor_id = self._find_neighbor_of_type(invoice_id, "VENDOR", nodes, adjacency)
            if vendor_id is None:
                status, reason = "unresolved", "Invoice not linked to any vendor"
            else:
                contract_id = self._find_neighbor_of_type(
                    vendor_id, "CONTRACT_AMOUNT", nodes, adjacency
                )
                if contract_id is None:
                    status, reason = "unresolved", "No matching vendor contract found"
                else:
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

        # Approval-limit flag is independent of match status.
        requires_approval = (
            invoice_amount is not None
            and approval_threshold is not None
            and invoice_amount > approval_threshold
        )

        return {
            "invoice_id": invoice_id,
            "status": status,
            "reason": reason,
            "invoice_amount": invoice_amount,
            "contract_amount": contract_amount,
            "requires_approval": requires_approval,
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
        approval_limits = {
            nid: nd for nid, nd in nodes.items()
            if _norm_type(nd.get("entity_type")) == "APPROVAL_LIMIT"
        }

        # Most conservative approval threshold across all APPROVAL_LIMIT nodes.
        approval_threshold: float | None = None
        for node in approval_limits.values():
            amount = _parse_amount(node.get("description"))
            if amount is not None:
                approval_threshold = (
                    amount if approval_threshold is None
                    else min(approval_threshold, amount)
                )

        results: list[dict] = []
        counts = {"matched": 0, "exception": 0, "unresolved": 0}
        for invoice_id, invoice in invoices.items():
            row = self._reconcile_one(
                invoice_id, invoice, nodes, adjacency, approval_threshold, text_chunks
            )
            results.append(row)
            counts[row["status"]] = counts.get(row["status"], 0) + 1

        total = len(invoices)
        match_rate = f"{round((counts['matched'] / total) * 100)}%" if total else "0%"

        return {
            "total": total,
            "matched": counts["matched"],
            "exceptions": counts["exception"],
            "unresolved": counts["unresolved"],
            "match_rate": match_rate,
            "results": results,
        }
