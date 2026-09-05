"""
Part B smoke test — B6: exercise all four compliance endpoints against a
synthetic in-memory workspace.

Run: python scripts/_partb_smoke.py

Calls each engine directly (no HTTP, no auth) with a hand-built graph
covering invoices, vendor, contract, approval limit, settlement, and a
tax line item with HSN code.  Confirms:
  - No unhandled exception from any engine
  - Each returns its documented response shape
  - forecast returns either a number dict or forecast_available=False
    (both are valid; thin-data 200 is not a failure)
"""
import sys
import types
import asyncio
from pathlib import Path

# ── stubs (same as conftest) ──────────────────────────────────────────────
_BD = str(Path(__file__).parent.parent / "backend")
def _stub():
    try:
        import sentence_transformers; return
    except ImportError: pass
    for _n, _p in [("backend", _BD), ("backend.llm", str(Path(_BD)/"llm")),
                   ("backend.config", str(Path(_BD)/"config"))]:
        if _n not in sys.modules:
            m = types.ModuleType(_n); m.__path__ = [_p]
            m.__package__ = _n; m.__spec__ = None; sys.modules[_n] = m
    for _n in ("backend.llm.client", "backend.config.settings"):
        if _n not in sys.modules: sys.modules[_n] = types.ModuleType(_n)
_stub()

from unittest.mock import AsyncMock, MagicMock, patch
from backend.compliance.reconciliation_engine import ReconciliationEngine as _RE

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
failures = []

def ok(cond, msg):
    tag = PASS if cond else FAIL
    print(f"  [{tag}] {msg}")
    if not cond:
        failures.append(msg)

def run(coro):
    return asyncio.run(coro)

def node(et, desc, sid=""):
    return {"entity_type": et, "description": desc, "source_id": sid}

# ─────────────────────────────────────────────────────────────────────────
# Synthetic workspace graph
# One vendor, one invoice (outflow), one contract with approval limit,
# one settlement (inflow), one tax line item with HSN code.
# ─────────────────────────────────────────────────────────────────────────
nodes = {
    # Reconciliation subgraph
    "inv1":  node("INVOICE_AMOUNT",  "\u20b950000 INV-2024-001 2024-01-15"),
    "v1":    node("VENDOR",          "Acme Corp"),
    "c1":    node("CONTRACT_AMOUNT", "\u20b9200000"),
    "al1":   node("APPROVAL_LIMIT",  "\u20b960000"),
    # Cashflow / settlement subgraph
    "set1":  node("SETTLEMENT_AMOUNT", "\u20b980000 settlement 2024-02-01"),
    "sd1":   node("SETTLEMENT_DATE",   "2024-02-01"),
    # Tax subgraph
    "tli1":  node("TAX_LINE_ITEM",   "Consulting \u20b940000 @ 18%"),
    "hsn1":  node("HSN_CODE",        "HSN 998314"),
    "rate1": node("TAX_RATE",        "18%"),
}
adjacency = {
    "inv1": {"v1"},
    "v1":   {"inv1", "c1", "al1"},
    "c1":   {"v1"},
    "al1":  {"v1"},
    "set1": {"sd1"},
    "sd1":  {"set1"},
    "tli1": {"hsn1"},
    "hsn1": {"tli1", "rate1"},
    "rate1":{"hsn1"},
}

def make_delegate(ws_id="ws-smoke"):
    with patch("backend.compliance.reconciliation_engine._get_pool"):
        delegate = _RE.__new__(_RE)
        delegate.workspace_id = ws_id
        delegate.working_dir  = "/tmp"
    delegate._load_nodes     = AsyncMock(return_value=nodes)
    delegate._load_adjacency = AsyncMock(return_value=adjacency)
    delegate._load_text_chunks = MagicMock(return_value={})
    return delegate

# ─────────────────────────────────────────────────────────────────────────
# 1. Reconciliation engine
# ─────────────────────────────────────────────────────────────────────────
print("\n=== Reconciliation ===")
try:
    with patch("backend.compliance.reconciliation_engine._get_pool"):
        eng = _RE.__new__(_RE)
        eng.workspace_id = "ws-smoke"
        eng.working_dir  = "/tmp"
    eng._load_nodes     = AsyncMock(return_value=nodes)
    eng._load_adjacency = AsyncMock(return_value=adjacency)
    eng._load_text_chunks = MagicMock(return_value={})

    result = run(eng.reconcile())
    ok(isinstance(result, dict),         "returns dict")
    ok("results" in result,              "has 'results' key")
    ok("total" in result,                "has 'total' key")
    ok(result["total"] >= 1,             f"at least 1 invoice processed (got {result['total']})")
    for row in result["results"]:
        ok("status" in row,              "each result row has 'status'")
        ok(row["status"] in ("matched","exception","unresolved"),
                                          f"status is valid: {row['status']}")
    print(f"  Summary: total={result['total']} matched={result.get('matched')} "
          f"exceptions={result.get('exceptions')} unresolved={result.get('unresolved')}")
except Exception as e:
    ok(False, f"Reconciliation raised: {e}")

# ─────────────────────────────────────────────────────────────────────────
# 2. Tax matcher
# ─────────────────────────────────────────────────────────────────────────
print("\n=== Tax Matcher ===")
try:
    from backend.compliance.tax_matcher import TaxMatcher
    with patch("backend.compliance.reconciliation_engine._get_pool"):
        tm = TaxMatcher.__new__(TaxMatcher)
        tm.workspace_id = "ws-smoke"
        tm.working_dir  = "/tmp"
        tm._delegate = make_delegate()

    result = run(tm.match())
    ok(isinstance(result, dict),          "returns dict")
    ok("results" in result,               "has 'results' key")
    ok("total" in result,                 "has 'total' key")
    ok("match_rate" in result,            "has 'match_rate' key")
    ok(result["total"] >= 1,              f"at least 1 tax line processed (got {result['total']})")
    for row in result["results"]:
        ok("status" in row,               "each result row has 'status'")
        ok(row["status"] in ("matched","exception","unresolved"),
                                           f"status is valid: {row['status']}")
    print(f"  Summary: total={result['total']} matched={result.get('matched')} "
          f"match_rate={result.get('match_rate')}")
except Exception as e:
    ok(False, f"TaxMatcher raised: {e}")

# ─────────────────────────────────────────────────────────────────────────
# 3. Cashflow extractor + aggregate_daily
# ─────────────────────────────────────────────────────────────────────────
print("\n=== Cashflow Extractor ===")
try:
    from backend.compliance.cashflow_extractor import CashflowExtractor, aggregate_daily
    with patch("backend.compliance.reconciliation_engine._get_pool"):
        ce = CashflowExtractor.__new__(CashflowExtractor)
        ce.workspace_id = "ws-smoke"
        ce.working_dir  = "/tmp"
        ce._delegate = make_delegate()

    events   = run(ce.extract())
    daily_df = aggregate_daily(events)
    ok(isinstance(events, list),                   "extract() returns list")
    ok(len(events) >= 1,                           f"at least 1 event extracted (got {len(events)})")
    for ev in events:
        ok("date"        in ev,                    "event has 'date'")
        ok("amount"      in ev,                    "event has 'amount'")
        ok("direction"   in ev,                    "event has 'direction'")
        ok("source_type" in ev,                    "event has 'source_type'")
        ok(ev["direction"] in ("inflow","outflow"), f"direction valid: {ev['direction']}")
    ok(not daily_df.empty,                         "aggregate_daily returns non-empty df")
    ok(set(daily_df.columns) >= {"date","net_flow","n_events"},
                                                   "daily df has required columns")
    print(f"  Events: {len(events)}  Daily rows: {len(daily_df)}")
    inflows  = [e for e in events if e["direction"] == "inflow"]
    outflows = [e for e in events if e["direction"] == "outflow"]
    print(f"  Inflows: {len(inflows)}  Outflows: {len(outflows)}")
except Exception as e:
    import traceback; traceback.print_exc()
    ok(False, f"CashflowExtractor raised: {e}")

# ─────────────────────────────────────────────────────────────────────────
# 4. Forecast logic (thin-data path — synthetic graph has < 14 dated days)
# ─────────────────────────────────────────────────────────────────────────
print("\n=== Forecast (thin-data path) ===")
try:
    from backend.ml.forecast_logic import _build_latest_feature_row, build_insufficient_history_response

    feature_row = _build_latest_feature_row(daily_df)

    if feature_row is None:
        # Expected: < 14 days of history
        response = build_insufficient_history_response()
        ok(response["forecast_available"] is False,
           "thin-data: forecast_available=False (correct — < 14 days)")
        ok(response.get("reason") == "insufficient historical data",
           "thin-data: reason string correct")
        ok("forecast_net_cashflow" not in response,
           "thin-data: no fabricated forecast number")
        print(f"  Response: {response}")
    else:
        # Enough history — would call models (not loaded here, just confirm shape)
        ok(feature_row.shape[1] == 9,
           f"feature row shape correct: {feature_row.shape}")
        print(f"  Sufficient history: feature_row shape={feature_row.shape}")
        print("  (Model prediction skipped in smoke test — no joblib files needed)")

except Exception as e:
    import traceback; traceback.print_exc()
    ok(False, f"Forecast logic raised: {e}")

# ─────────────────────────────────────────────────────────────────────────
print()
if failures:
    print(f"\033[31m{len(failures)} FAILURE(S):\033[0m")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\033[32mAll smoke tests passed.\033[0m")
