"""
Part B verification checks — route collision, entity schema, shared utilities.
Run: python scripts/_partb_checks.py
"""
import ast
import pathlib
import re
import sys

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
MISS = "\033[33mMISS\033[0m"
failures = []

def ok(cond, msg):
    tag = PASS if cond else FAIL
    print(f"  [{tag}] {msg}")
    if not cond:
        failures.append(msg)

# ===========================================================================
# B3 — Route collision check
# ===========================================================================
print("\n=== B3: Route collision check ===\n")

main_src = pathlib.Path("backend/api/main.py").read_text(encoding="utf-8")
routers = re.findall(r"include_router\(\s*(\w+)", main_src)
print("Routers registered in main.py:")
for r in routers:
    print(f"    {r}")

route_files = {
    "reconcile":     "backend/api/routes/reconciliation.py",
    "settlement-qa": "backend/api/routes/workspace_settlement_qa.py",
    "tax-match":     "backend/api/routes/tax_matching.py",
    "forecast":      "backend/api/routes/forecast.py",
    "cashflow":      "backend/api/routes/cashflow.py",
}

print()
# Collect all decorated route paths across all route files
all_decorator_paths: list[tuple[str, str]] = []
for slug, fpath in route_files.items():
    src = pathlib.Path(fpath).read_text(encoding="utf-8")
    tree = ast.parse(src)
    # Also get the router prefix
    prefix_m = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', src)
    prefix = prefix_m.group(1) if prefix_m else ""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                unparsed = ast.unparse(dec)
                if ".post(" in unparsed or ".get(" in unparsed or ".put(" in unparsed:
                    # Extract just the path argument
                    path_m = re.search(r'["\']([^"\']+)["\']', unparsed)
                    if path_m:
                        full = prefix + path_m.group(1)
                        all_decorator_paths.append((full, fpath.split("/")[-1]))

print("All route paths (prefix + path):")
seen: dict[str, str] = {}
for full_path, fname in all_decorator_paths:
    collision = full_path in seen
    tag = FAIL if collision else PASS
    print(f"  [{tag}] {full_path:50s}  in {fname}")
    if collision:
        failures.append(f"COLLISION: {full_path} in {fname} AND {seen[full_path]}")
    seen[full_path] = fname

# Specifically confirm the four required paths
required_paths = [
    "/workspace/{case_id}/reconcile",
    "/workspace/{case_id}/settlement-qa",
    "/workspace/{case_id}/tax-match",
    "/workspace/{case_id}/forecast",
]
print()
print("Required-path presence:")
for rp in required_paths:
    ok(rp in seen, f"{rp} registered")

# ===========================================================================
# B4 — Entity schema check
# ===========================================================================
print("\n=== B4: Entity schema check ===\n")

prompt_src = pathlib.Path("backend/core/prompt.py").read_text(encoding="utf-8")
# DEFAULT_ENTITY_TYPES is stored as PROMPTS["DEFAULT_ENTITY_TYPES"] = [...]
m = re.search(r'PROMPTS\["DEFAULT_ENTITY_TYPES"\]\s*=\s*\[(.*?)\]', prompt_src, re.DOTALL)
if not m:
    print("  [FAIL] PROMPTS['DEFAULT_ENTITY_TYPES'] not found in prompt.py")
    failures.append("DEFAULT_ENTITY_TYPES not found")
    types_in_schema: set[str] = set()
else:
    types_in_schema = set(re.findall(r'"([A-Z][A-Z_]+)"', m.group(1)))
    print("Types in PROMPTS['DEFAULT_ENTITY_TYPES']:")
    for t in sorted(types_in_schema):
        print(f"    {t}")

required_types = {
    # reconciliation_engine.py
    "VENDOR", "INVOICE", "INVOICE_AMOUNT", "CONTRACT_AMOUNT",
    "PAYMENT_TERMS", "DUE_DATE", "APPROVAL_LIMIT",
    # cashflow_extractor.py
    "SETTLEMENT_AMOUNT", "SETTLEMENT_DATE",
    # settlement QA (from task description)
    "SETTLEMENT_ID", "PAYOUT_STATUS", "FEE_DEDUCTION", "UTR_NUMBER",
    # tax_matcher.py
    "TAX_LINE_ITEM", "GST_NUMBER", "TAX_RATE", "HSN_CODE",
}

print()
print("Coverage check (types used in compliance code):")
missing_types = []
for t in sorted(required_types):
    present = t in types_in_schema
    tag = PASS if present else MISS
    print(f"  [{tag}] {t}")
    if not present:
        missing_types.append(t)
        failures.append(f"Entity type missing from schema: {t}")

# ===========================================================================
# B5 — Shared-utility check
# ===========================================================================
print("\n=== B5: Shared-utility check ===\n")

compliance_files = {
    "reconciliation_engine": "backend/compliance/reconciliation_engine.py",
    "tax_matcher":           "backend/compliance/tax_matcher.py",
    "cashflow_extractor":    "backend/compliance/cashflow_extractor.py",
}

shared_helpers = {"_norm_type", "_parse_amount", "_parse_date"}

for name, fpath in compliance_files.items():
    src = pathlib.Path(fpath).read_text(encoding="utf-8")
    tree = ast.parse(src)

    local_fns = {n.name for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef)}

    imports_from: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports_from.append((node.module, alias.name))

    reimplemented = shared_helpers & local_fns
    imported_shared = [(mod, fn) for mod, fn in imports_from if fn in shared_helpers]

    print(f"  {name}:")
    print(f"    Imports shared helpers: {imported_shared}")
    print(f"    Local reimplementations: {sorted(reimplemented)}")

    if name == "reconciliation_engine":
        # This is the source — it MUST define all three
        ok(shared_helpers <= local_fns,
           f"{name} defines all three shared helpers (is the source)")
        ok(not any(fn in dict(imports_from) for fn in shared_helpers),
           f"{name} does NOT import helpers from another module (it IS the source)")
    else:
        # Downstream modules MUST import, never reimplement
        ok(not reimplemented,
           f"{name} has no local reimplementation of {shared_helpers} (got {reimplemented})")
        imported_names = {fn for _, fn in imported_shared}
        ok(shared_helpers <= imported_names or name == "tax_matcher",
           f"{name} imports all three shared helpers from reconciliation_engine")
        # tax_matcher only needs _norm_type (it doesn't parse amounts/dates directly)
        if name == "tax_matcher":
            ok("_norm_type" in imported_names,
               "tax_matcher imports _norm_type from reconciliation_engine")
            ok("_parse_amount" not in local_fns,
               "tax_matcher has no local _parse_amount")
            ok("_parse_date" not in local_fns,
               "tax_matcher has no local _parse_date")

# ===========================================================================
# Summary
# ===========================================================================
print()
if failures:
    print(f"\033[31m{len(failures)} FINDING(S):\033[0m")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\033[32mAll Part B checks passed.\033[0m")
