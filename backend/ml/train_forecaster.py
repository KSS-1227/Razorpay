"""
Cashflow Forecaster — Training Script

Enterprise Compliance Intelligence Platform

Purpose
-------
Standalone script run ONCE manually before the demo (or in CI).
NOT called at API request time.

Given a workspace's daily net-cash-flow series (produced by Part 1's
``aggregate_daily``), it:

  1. Builds the supervised feature table (Part 2's ``build_feature_table``).
  2. Splits into a chronological 80/20 train/test split.
  3. Trains three quantile regressors using scikit-learn's
     GradientBoostingRegressor (``loss="quantile"``):
       - p10  (alpha=0.10) — lower bound of 80 % prediction interval
       - p50  (alpha=0.50) — point forecast (median)
       - p90  (alpha=0.90) — upper bound of 80 % prediction interval
  4. Evaluates on the held-out test split:
       - MAE of the p50 median model
       - Calibration: % of test points where true target ∈ [p10, p90]
         (should be ~80 % for an honest interval)
  5. Saves the three models to backend/ml/artifacts/ as
     forecaster_p10.joblib, forecaster_p50.joblib, forecaster_p90.joblib.
  6. Writes backend/ml/artifacts/forecaster_meta.json with provenance and
     evaluation metrics.

Why GradientBoostingRegressor instead of LightGBM / XGBoost
------------------------------------------------------------
Neither LightGBM nor XGBoost is present in this project's requirements.txt.
scikit-learn ships GradientBoostingRegressor with native quantile-loss support
(sklearn >= 1.0), which is already installed (sklearn 1.8.0, joblib 1.5.3).
Adding a new heavy dependency for a marginal accuracy gain on a small dataset
would be a bad tradeoff.  The hyperparameters below (n_estimators=100,
max_depth chosen via num_leaves≈15 → depth=4, learning_rate=0.1) replicate the
original LightGBM spec as closely as sklearn's API allows.

Hyperparameters
---------------
Fixed, not tuned — see task description for the rationale.

    n_estimators  = 100
    max_depth     = 4       (≈ num_leaves=15 in LightGBM; 2^4 = 16 leaves)
    learning_rate = 0.1
    subsample     = 0.8     (row subsampling — mild regularisation for small data)
    min_samples_leaf = 3    (prevents single-sample leaves on tiny datasets)

Usage
-----
  # Recommended: run the top-level wrapper script (avoids the backend package
  # init chain which requires sentence-transformers):
  python scripts/train_forecaster.py \\
      --workspace-id  <case_id>         \\
      --working-dir   path/to/working/  \\
      [--horizon-days 7]                \\
      [--artifacts-dir backend/ml/artifacts]

  # Or import and call programmatically (the import stubs must already be in
  # place — see conftest.py or scripts/train_forecaster.py for the pattern):
  from backend.ml.train_forecaster import train_and_save
  meta = train_and_save(daily_df, horizon_days=7)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from backend.ml.features import (
    FEATURE_COLUMNS,
    FeatureTable,
    build_feature_table,
    train_test_split_temporal,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fixed hyperparameters — do NOT tune; see module docstring.
_HPARAMS: dict[str, Any] = {
    "n_estimators":    100,
    "max_depth":       4,       # ≈ num_leaves=15 (2^4 = 16 leaves max)
    "learning_rate":   0.1,
    "subsample":       0.8,
    "min_samples_leaf": 3,
    "random_state":    42,
}

# Quantiles trained
_QUANTILES = {"p10": 0.10, "p50": 0.50, "p90": 0.90}

# Rows below this threshold trigger a low-data warning in meta.json.
_LOW_DATA_THRESHOLD = 30

# Default output directory (relative to the repo root when run as __main__).
_DEFAULT_ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


# ---------------------------------------------------------------------------
# Core training function (importable, no I/O side-effects)
# ---------------------------------------------------------------------------

def train_quantile_models(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    """Train three quantile regressors and return evaluation metrics + models.

    Parameters
    ----------
    train_df, test_df:
        Chronological splits from ``train_test_split_temporal``.  Both must
        contain all ``FEATURE_COLUMNS`` plus a ``target`` column.

    Returns
    -------
    dict with keys:
        "models"       — {quantile_name: fitted GradientBoostingRegressor}
        "mae"          — float, MAE of the p50 model on the test set
        "calibration"  — float in [0, 1], fraction of test rows inside [p10, p90]
        "n_train"      — int
        "n_test"       — int
        "predictions"  — DataFrame(index=test_df.index, columns=[p10, p50, p90])
    """
    X_train = train_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_train = train_df["target"].to_numpy(dtype=float)
    X_test  = test_df[FEATURE_COLUMNS].to_numpy(dtype=float)
    y_test  = test_df["target"].to_numpy(dtype=float)

    models: dict[str, GradientBoostingRegressor] = {}

    for name, alpha in _QUANTILES.items():
        mdl = GradientBoostingRegressor(loss="quantile", alpha=alpha, **_HPARAMS)
        mdl.fit(X_train, y_train)
        models[name] = mdl
        logger.info("Trained %s model (alpha=%.2f)  n_train=%d", name, alpha, len(X_train))

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    preds_p10 = models["p10"].predict(X_test)
    preds_p50 = models["p50"].predict(X_test)
    preds_p90 = models["p90"].predict(X_test)

    mae = float(np.mean(np.abs(preds_p50 - y_test)))

    # Calibration: fraction of test points where true target ∈ [p10, p90].
    inside = (y_test >= preds_p10) & (y_test <= preds_p90)
    calibration = float(inside.mean())

    predictions = pd.DataFrame(
        {"p10": preds_p10, "p50": preds_p50, "p90": preds_p90},
        index=test_df.index,
    )

    return {
        "models":      models,
        "mae":         mae,
        "calibration": calibration,
        "n_train":     int(len(X_train)),
        "n_test":      int(len(X_test)),
        "predictions": predictions,
    }


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def save_models(
    models: dict[str, GradientBoostingRegressor],
    artifacts_dir: Path,
) -> dict[str, Path]:
    """Persist each model to a .joblib file.  Returns {name: path}."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, mdl in models.items():
        dest = artifacts_dir / f"forecaster_{name}.joblib"
        joblib.dump(mdl, dest)
        paths[name] = dest
        logger.info("Saved %s → %s", name, dest)
    return paths


def save_meta(
    meta: dict[str, Any],
    artifacts_dir: Path,
) -> Path:
    """Write forecaster_meta.json.  Returns the path written."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    dest = artifacts_dir / "forecaster_meta.json"
    dest.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Saved meta → %s", dest)
    return dest


# ---------------------------------------------------------------------------
# High-level entry point (importable)
# ---------------------------------------------------------------------------

def train_and_save(
    daily_df: pd.DataFrame,
    horizon_days: int = 7,
    artifacts_dir: Path | str = _DEFAULT_ARTIFACTS_DIR,
) -> dict[str, Any]:
    """Full pipeline: features → train → evaluate → save.

    Parameters
    ----------
    daily_df:
        Output of ``aggregate_daily`` (columns: date, net_flow, n_events).
    horizon_days:
        Forecast horizon passed to ``build_feature_table``.
    artifacts_dir:
        Directory where models and meta.json are written.

    Returns
    -------
    The meta dict that was written to forecaster_meta.json.  Contains:

        training_date       — ISO-8601 UTC timestamp
        horizon_days        — int
        n_training_rows     — int
        n_test_rows         — int
        mae                 — float
        calibration_pct     — float (0-100), % of test points inside [p10, p90]
        low_data_warning    — bool, true when n_training_rows < 30
        model_paths         — {p10, p50, p90}: relative path strings

    Raises
    ------
    ValueError
        When the feature table is empty after filtering (no usable rows at all).
    """
    artifacts_dir = Path(artifacts_dir)

    # --- Part 2: build feature table ---
    ft: FeatureTable = build_feature_table(daily_df, horizon_days=horizon_days)

    if ft.full.empty:
        raise ValueError(
            f"Feature table is empty after filtering "
            f"(need at least {14 + horizon_days} days of cashflow data). "
            f"Input had {len(daily_df)} rows."
        )

    # --- chronological split ---
    # train_test_split_temporal raises if < 2 rows; we need ≥ 2.
    if len(ft.full) < 2:
        raise ValueError(
            f"Only {len(ft.full)} feature row — need at least 2 to split "
            f"train/test.  Collect more cashflow data."
        )

    train_df, test_df = train_test_split_temporal(ft.full, test_fraction=0.2)

    n_train = len(train_df)

    # --- train ---
    result = train_quantile_models(train_df, test_df)

    # --- save models ---
    model_paths = save_models(result["models"], artifacts_dir)

    # --- compose meta ---
    meta: dict[str, Any] = {
        "training_date":    datetime.now(tz=timezone.utc).isoformat(),
        "horizon_days":     horizon_days,
        "n_training_rows":  result["n_train"],
        "n_test_rows":      result["n_test"],
        "mae":              round(result["mae"], 4),
        "calibration_pct":  round(result["calibration"] * 100, 2),
        "low_data_warning": n_train < _LOW_DATA_THRESHOLD,
        "model_paths": {
            name: str(path.relative_to(artifacts_dir.parent))
            for name, path in model_paths.items()
        },
    }

    save_meta(meta, artifacts_dir)

    return meta


# ---------------------------------------------------------------------------
# CLI — run manually before demo
# ---------------------------------------------------------------------------

def _print_summary(meta: dict[str, Any]) -> None:
    """Print a plain-text evaluation summary to stdout."""
    warn = "  *** LOW DATA WARNING — fewer than 30 training rows ***" if meta["low_data_warning"] else ""
    print()
    print("=" * 60)
    print("  Cashflow Forecaster — Training Complete")
    print("=" * 60)
    print(f"  Horizon:          {meta['horizon_days']} days")
    print(f"  Training rows:    {meta['n_training_rows']}{warn}")
    print(f"  Test rows:        {meta['n_test_rows']}")
    print(f"  MAE (p50):        {meta['mae']:,.2f}")
    print(f"  Calibration:      {meta['calibration_pct']:.1f}%  "
          f"(% test points inside 80% interval)")
    print(f"  Training date:    {meta['training_date']}")
    print()
    for name, path in meta["model_paths"].items():
        print(f"  Saved {name}:  {path}")
    print("=" * 60)
    print()


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Train the cashflow quantile forecaster for a workspace.  "
            "Run once manually before the demo — NOT called at API request time."
        )
    )
    p.add_argument(
        "--workspace-id", required=True,
        help="Case / workspace ID (used to load cashflow data from CockroachDB).",
    )
    p.add_argument(
        "--working-dir", required=True,
        help="Path to the workspace working directory (contains kv_store_text_chunks.json).",
    )
    p.add_argument(
        "--horizon-days", type=int, default=7,
        help="Forecast horizon in days (default: 7).",
    )
    p.add_argument(
        "--artifacts-dir",
        default=str(_DEFAULT_ARTIFACTS_DIR),
        help="Directory to write model files and meta.json (default: backend/ml/artifacts).",
    )
    p.add_argument(
        "--csv",
        default=None,
        help=(
            "Load cashflow data from a CSV file instead of CockroachDB.  "
            "CSV must have columns: date (YYYY-MM-DD), net_flow, n_events.  "
            "Useful for offline / demo preparation without a live DB."
        ),
    )
    return p


def _load_daily_from_csv(csv_path: str) -> pd.DataFrame:
    """Read a pre-exported aggregate_daily CSV.  Converts date strings to date objects."""
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["net_flow"] = df["net_flow"].astype(float)
    df["n_events"] = df["n_events"].astype(int)
    return df


async def _load_daily_from_db(workspace_id: str, working_dir: str) -> pd.DataFrame:
    """Async: extract cashflow events from CockroachDB and aggregate to daily."""
    from backend.compliance.cashflow_extractor import CashflowExtractor, aggregate_daily
    extractor = CashflowExtractor(workspace_id=workspace_id, working_dir=working_dir)
    events = await extractor.extract()
    return aggregate_daily(events)


def _apply_import_stubs() -> None:
    """Prevent backend/__init__.py from triggering the sentence-transformers
    import chain when this script is run directly (``python -m backend.ml.train_forecaster``).

    The training script only needs ``backend.ml.features`` and (optionally)
    ``backend.compliance.cashflow_extractor``.  The LLM/embedding stack is never
    required here and crashes on machines without sentence-transformers installed.

    This mirrors the root conftest.py approach: stub the top-level ``backend``
    package with the real ``__path__`` so sub-packages remain importable, then
    stub the two modules that call ``get_embed_model()`` at import time.
    """
    import sys
    import types
    try:
        import sentence_transformers  # noqa: F401
        return  # full deps installed — nothing to do
    except ImportError:
        pass

    from pathlib import Path as _Path
    _bd = str(_Path(__file__).parent.parent)   # .../backend/

    for _name, _path in [
        ("backend",        _bd),
        ("backend.llm",    str(_Path(_bd) / "llm")),
        ("backend.config", str(_Path(_bd) / "config")),
    ]:
        if _name not in sys.modules:
            _m = types.ModuleType(_name)
            _m.__path__    = [_path]
            _m.__package__ = _name
            _m.__spec__    = None
            sys.modules[_name] = _m

    for _name in ("backend.llm.client", "backend.config.settings"):
        if _name not in sys.modules:
            sys.modules[_name] = types.ModuleType(_name)


def main(argv: list[str] | None = None) -> None:
    # Must be the very first thing in main() — before any backend.* import
    # that would otherwise chain into backend/__init__.py → sentence_transformers.
    _apply_import_stubs()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.csv:
        logger.info("Loading daily cashflow from CSV: %s", args.csv)
        daily_df = _load_daily_from_csv(args.csv)
    else:
        # DB path — requires an async context.
        import asyncio
        logger.info(
            "Loading cashflow from CockroachDB  workspace=%s", args.workspace_id
        )
        daily_df = asyncio.run(
            _load_daily_from_db(args.workspace_id, args.working_dir)
        )

    logger.info(
        "Daily series: %d rows  (%s → %s)",
        len(daily_df),
        daily_df["date"].min() if not daily_df.empty else "n/a",
        daily_df["date"].max() if not daily_df.empty else "n/a",
    )

    try:
        meta = train_and_save(
            daily_df,
            horizon_days=args.horizon_days,
            artifacts_dir=Path(args.artifacts_dir),
        )
    except ValueError as exc:
        logger.error("Training aborted: %s", exc)
        sys.exit(1)

    _print_summary(meta)


if __name__ == "__main__":
    main()
