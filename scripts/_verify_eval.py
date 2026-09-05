"""Verify evaluate_forecaster.py behaviour. Run: python scripts/_verify_eval.py"""
import json, os, tempfile, pathlib, subprocess, sys

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
failures = []

def check(cond, msg):
    print(f"  [{ PASS if cond else FAIL }] {msg}")
    if not cond:
        failures.append(msg)

def run_eval(artifacts_dir: pathlib.Path) -> tuple[int, str, str]:
    """Run evaluate_forecaster.py capturing output safely on Windows."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    r = subprocess.run(
        [sys.executable, "-X", "utf8", "eval/evaluate_forecaster.py",
         "--artifacts-dir", str(artifacts_dir)],
        capture_output=True,
        env=env,
    )
    # Decode bytes explicitly — avoids Windows cp1252 pipe issues
    stdout = r.stdout.decode("utf-8", errors="replace")
    stderr = r.stderr.decode("utf-8", errors="replace")
    return r.returncode, stdout, stderr


# ---- Test 1: low_data_warning=True ----------------------------------------
d = pathlib.Path(tempfile.mkdtemp())
meta = {
    "training_date": "2026-09-05T06:00:00+00:00",
    "horizon_days": 7,
    "n_training_rows": 12,
    "n_test_rows": 3,
    "mae": 850.5,
    "calibration_pct": 33.3,
    "low_data_warning": True,
    "model_paths": {}
}
(d / "forecaster_meta.json").write_text(json.dumps(meta), encoding="utf-8")

rc, out, err = run_eval(d)
print("--- stdout (low_data_warning=True) ---")
print(out)
print("--- stderr ---")
print(err or "(none)")
print("--- end ---")

check(rc == 0,            "exits 0 with valid meta.json")
check("12 days" in out,   "n_training_rows (12 days) in output")
check("850" in out,       "MAE (850) in output")
check("33.3%" in out,     "calibration_pct (33.3%) in output")
check("Low-data" in out,  "Low-data warning section printed")
check("7-day" in out,     "horizon_days in output")
check("2026-09-05" in out,"training date in output")

# ---- Test 2: low_data_warning=False (no warning section) ------------------
d2 = pathlib.Path(tempfile.mkdtemp())
meta2 = {**meta, "low_data_warning": False, "n_training_rows": 50,
         "calibration_pct": 75.0}
(d2 / "forecaster_meta.json").write_text(json.dumps(meta2), encoding="utf-8")

rc2, out2, _ = run_eval(d2)
check("Low-data" not in out2, "No low-data warning when low_data_warning=False")
check("75.0%" in out2,        "calibration_pct (75.0%) printed")
check("50 days" in out2,      "n_training_rows (50 days) printed")

# ---- Test 3: missing file → exit 1 ----------------------------------------
rc3, _, err3 = run_eval(pathlib.Path(tempfile.mkdtemp()))
check(rc3 == 1,
      f"missing meta.json exits with code 1 (got {rc3})")
check("forecaster_meta.json not found" in err3,
      "helpful error message on stderr")

# ---- Test 4: default artifacts dir resolves correctly ---------------------
src = pathlib.Path("eval/evaluate_forecaster.py").read_text(encoding="utf-8")
check(
    '"ml" / "artifacts"' in src or "'ml' / 'artifacts'" in src,
    "default artifacts dir points to backend/ml/artifacts",
)

print()
if failures:
    print(f"\033[31m{len(failures)} FAILURE(S):\033[0m")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\033[32mAll checks passed.\033[0m")
