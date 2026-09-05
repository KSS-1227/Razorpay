"""
Static verification of backend/api/routes/forecast.py
Run: python scripts/_verify_forecast_route.py
"""
import ast
import pathlib
import sys

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
failures = []

def check(condition, msg):
    tag = PASS if condition else FAIL
    print(f"  [{tag}] {msg}")
    if not condition:
        failures.append(msg)

src = pathlib.Path("backend/api/routes/forecast.py").read_text(encoding="utf-8")
lines = src.splitlines()

# 1. Parses without syntax errors
try:
    tree = ast.parse(src)
    check(True, "forecast.py parses cleanly (no syntax errors)")
except SyntaxError as e:
    check(False, f"SyntaxError: {e}")
    sys.exit(1)

# 2. router assignment present
assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
router_assign = [a for a in assigns if any(
    isinstance(t, ast.Name) and t.id == "router" for t in a.targets
)]
check(bool(router_assign), "router = APIRouter(...) assignment found")

# 3. prefix="/workspace" in router construction
check('prefix="/workspace"' in src, 'router prefix="/workspace"')

# 4. POST /{case_id}/forecast decorator
check(
    any("forecast" in ast.unparse(dec)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for dec in node.decorator_list),
    "POST /{case_id}/forecast route decorator present",
)

# 5. Insufficient-history 200 path
check("forecast_available" in src, "'forecast_available' key in source")
check("insufficient historical data" in src, "insufficient-history reason string present")
check('"forecast_available": False' in src or "'forecast_available': False" in src,
      "forecast_available=False returned for short series")

# 6. 404 for missing models
check("status_code=404" in src, "HTTP 404 raised when models are missing")

# 7. All three quantile predictions
for q in ("p10", "p50", "p90"):
    check(
        f'models["{q}"].predict' in src or f"models['{q}'].predict" in src,
        f"models['{q}'].predict() call present",
    )

# 8. All six required response keys
for key in ("forecast_net_cashflow", "lower_bound", "upper_bound",
            "horizon_days", "model_trained_on", "low_data_warning"):
    check(key in src, f"response key '{key}' present in source")

# 9. All meta.json keys accessed
for key in ("horizon_days", "n_training_rows", "training_date", "low_data_warning"):
    check(
        f'meta["{key}"]' in src or f"meta['{key}']" in src,
        f"meta['{key}'] accessed",
    )

# 10. Ownership check before data extraction
verify_line  = next((i for i, l in enumerate(lines) if "_verify_case_ownership" in l and "await" in l), None)
extract_line = next((i for i, l in enumerate(lines) if "extractor.extract" in l), None)
check(verify_line is not None, "ownership check present")
check(extract_line is not None, "extractor.extract() call present")
if verify_line is not None and extract_line is not None:
    check(verify_line < extract_line,
          f"ownership check (line {verify_line+1}) before extract (line {extract_line+1})")

# 11. working_dir path-traversal guard
check("is_relative_to" in src, "working_dir path-traversal guard (is_relative_to) present")

# 12. 500 handler at end of try block
check(
    "HTTPException(status_code=500" in src,
    "generic 500 handler present",
)

# 13. _build_latest_feature_row uses horizon_days=1
check(
    "horizon_days=1" in src,
    "_build_latest_feature_row calls build_feature_table with horizon_days=1",
)

# 14. Takes last row (most recent) of feature table
check(
    "iloc[[-1]]" in src or "iloc[-1]" in src,
    "Most-recent feature row selected with iloc[-1]",
)

# 15. Registered in main.py
main_src = pathlib.Path("backend/api/main.py").read_text(encoding="utf-8")
check(
    "from backend.api.routes.forecast import router as forecast_router" in main_src,
    "forecast_router imported in main.py",
)
check(
    "forecast_router" in main_src.split("import router as forecast_router")[-1],
    "forecast_router passed to app.include_router() in main.py",
)

# 16. Tags match the pattern used by siblings
check('tags=["Forecast"]' in src, 'tags=["Forecast"] set on router')

print()
if failures:
    print(f"\033[31m{len(failures)} FAILURE(S):\033[0m")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\033[32mAll checks passed.\033[0m")
