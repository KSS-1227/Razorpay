#!/usr/bin/env python
"""
Wrapper script for backend/ml/train_forecaster.py

Run this file directly instead of ``python -m backend.ml.train_forecaster``.
Direct file execution avoids triggering ``backend/__init__.py``'s eager import
of MMKGBuilder → sentence_transformers, which is not needed for training and is
not installed on every machine.

Usage (from repo root)
----------------------
  python scripts/train_forecaster.py --workspace-id <case_id> --working-dir <path>

  # Load from a pre-exported CSV instead of CockroachDB:
  python scripts/train_forecaster.py --workspace-id demo --working-dir . \\
      --csv path/to/daily_cashflow.csv

All flags are forwarded to backend.ml.train_forecaster.main().
"""
import sys
import types
from pathlib import Path

# ------------------------------------------------------------------ #
# Stub the heavy ML import chain BEFORE any backend.* import          #
# ------------------------------------------------------------------ #
# backend/__init__.py imports MMKGBuilder which pulls in the LLM stack
# and crashes with "sentence_transformers not installed" on machines
# that only have the compliance/forecasting deps.  The stubs below let
# Python discover backend.ml.* and backend.compliance.* normally while
# silently skipping the parts we don't need.

_BACKEND_DIR = str(Path(__file__).parent.parent / "backend")


def _install_stubs() -> None:
    try:
        import sentence_transformers  # noqa: F401
        return  # full env — nothing to stub
    except ImportError:
        pass

    for _name, _path in [
        ("backend",        _BACKEND_DIR),
        ("backend.llm",    str(Path(_BACKEND_DIR) / "llm")),
        ("backend.config", str(Path(_BACKEND_DIR) / "config")),
    ]:
        if _name not in sys.modules:
            m = types.ModuleType(_name)
            m.__path__    = [_path]
            m.__package__ = _name
            m.__spec__    = None
            sys.modules[_name] = m

    for _name in ("backend.llm.client", "backend.config.settings"):
        if _name not in sys.modules:
            sys.modules[_name] = types.ModuleType(_name)


_install_stubs()

# ------------------------------------------------------------------ #
# Add repo root to sys.path so backend.* is importable               #
# ------------------------------------------------------------------ #
_REPO_ROOT = str(Path(__file__).parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ------------------------------------------------------------------ #
# Hand off to the real main()                                          #
# ------------------------------------------------------------------ #
from backend.ml.train_forecaster import main  # noqa: E402

if __name__ == "__main__":
    main()
