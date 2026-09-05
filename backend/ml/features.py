"""
Feature Engineering — Cashflow Forecasting

Enterprise Compliance Intelligence Platform

Purpose
-------
Turn the gapless daily net-cash-flow DataFrame produced by
``backend.compliance.cashflow_extractor.aggregate_daily`` into a supervised
learning table of lag features.  No model lives here — this module only
builds the input matrix and labels that a model in the next step will
consume.

Design constraints
------------------
- Lag-only features: fast to compute, interpretable, work on small datasets.
- Minimum history guard: rows with fewer than 14 prior days of history are
  dropped so every lag/rolling feature is non-NaN.
- No lookahead fabrication: rows whose target window extends past the last
  available day are dropped.  A row that would need days not yet in the data
  must never appear in the table.
- Chronological split only: train/test split preserves time order so the
  evaluation reflects the real forecasting scenario.

Public API
----------
``build_feature_table(daily_df, horizon_days=7)``
    Returns a ``FeatureTable`` named-tuple with fields:

        features  — pandas.DataFrame of input columns (X)
        targets   — pandas.Series of float targets (y), index-aligned with features
        full      — pandas.DataFrame: features + ``target`` column together

``train_test_split_temporal(full_df, test_fraction=0.2)``
    Returns ``(train_df, test_df)`` split at ~80/20 by date order, never
    shuffled.

Input contract
--------------
``daily_df`` must be the DataFrame returned by ``aggregate_daily``:

    date       — Python ``datetime.date`` objects (not strings, not Timestamps)
    net_flow   — float (positive = inflow, negative = outflow)
    n_events   — int

The frame must be sorted by date ascending and have no duplicate dates; both
guarantees hold for any frame produced by ``aggregate_daily``.
"""
from __future__ import annotations

from typing import NamedTuple

import pandas as pd


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class FeatureTable(NamedTuple):
    """Return value of ``build_feature_table``."""
    features: pd.DataFrame   # input matrix — no target column
    targets:  pd.Series      # aligned target series (name="target")
    full:     pd.DataFrame   # features + "target" column in one frame


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Number of prior days required before a row is included.
# 14 satisfies the lag_14 and rolling_mean_14 features.
_MIN_HISTORY = 14

# Feature column order (stable, predictable for downstream consumers).
FEATURE_COLUMNS = [
    "lag_1",
    "lag_3",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_std_7",
    "day_of_week",
    "n_events_lag_7",
]


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_feature_table(
    daily_df: pd.DataFrame,
    horizon_days: int = 7,
) -> FeatureTable:
    """Build a supervised feature table from a gapless daily cashflow series.

    Parameters
    ----------
    daily_df:
        Output of ``aggregate_daily`` — columns ``[date, net_flow, n_events]``,
        one row per calendar day, no gaps.
    horizon_days:
        Forecast horizon.  The ``target`` for day *t* is the sum of
        ``net_flow`` over *[t, t + horizon_days)* — i.e. the next
        ``horizon_days`` days starting **from** day *t* itself.

    Returns
    -------
    FeatureTable
        Named-tuple with ``.features``, ``.targets``, and ``.full``.
        All three share the same integer RangeIndex after reset.
        Returns an empty ``FeatureTable`` (all three empty) when the input
        has fewer rows than ``_MIN_HISTORY + horizon_days``.

    Raises
    ------
    ValueError
        If ``daily_df`` is missing required columns or ``horizon_days < 1``.
    """
    if horizon_days < 1:
        raise ValueError(f"horizon_days must be >= 1, got {horizon_days}")

    required = {"date", "net_flow", "n_events"}
    missing = required - set(daily_df.columns)
    if missing:
        raise ValueError(f"daily_df is missing columns: {missing}")

    if daily_df.empty:
        return _empty_table()

    # Work on a clean copy sorted by date; reset to a predictable integer index.
    df = daily_df[["date", "net_flow", "n_events"]].copy()
    df = df.sort_values("date").reset_index(drop=True)

    n = len(df)

    # ------------------------------------------------------------------
    # Lag features (shift by k positions; k days back in a gapless series)
    # ------------------------------------------------------------------
    df["lag_1"]  = df["net_flow"].shift(1)
    df["lag_3"]  = df["net_flow"].shift(3)
    df["lag_7"]  = df["net_flow"].shift(7)
    df["lag_14"] = df["net_flow"].shift(14)

    # ------------------------------------------------------------------
    # Rolling features (window ends at row i-1, i.e. strictly past data)
    # using closed="left" so row t does not see its own value.
    # pandas rolling default is closed="right" (includes current row) so we
    # shift by 1 and use min_periods to avoid NaN contamination.
    # ------------------------------------------------------------------
    past_flow = df["net_flow"].shift(1)   # one-step-back series
    df["rolling_mean_7"]  = past_flow.rolling(window=7,  min_periods=7).mean()
    df["rolling_mean_14"] = past_flow.rolling(window=14, min_periods=14).mean()
    df["rolling_std_7"]   = past_flow.rolling(window=7,  min_periods=7).std()

    # ------------------------------------------------------------------
    # Calendar feature
    # ------------------------------------------------------------------
    # date column holds Python datetime.date objects; .weekday() is 0=Mon..6=Sun
    df["day_of_week"] = df["date"].apply(lambda d: d.weekday())

    # ------------------------------------------------------------------
    # Activity proxy: sum of n_events over the trailing 7 days (rows i-7..i-1)
    # ------------------------------------------------------------------
    past_events = df["n_events"].shift(1)
    df["n_events_lag_7"] = past_events.rolling(window=7, min_periods=7).sum()

    # ------------------------------------------------------------------
    # Target: sum of net_flow over [t, t + horizon_days)
    # horizon_days rows starting at the current row (inclusive).
    # We use a forward-looking rolling sum via shift(-horizon_days+1) then
    # rolling on the reversed direction — simpler: just sum a shifted matrix.
    # ------------------------------------------------------------------
    # rolling(horizon_days).sum() on the *forward* direction:
    # value at index i = sum of rows [i, i+horizon_days-1]
    # We achieve this by reversing, rolling, reversing back.
    fwd_sum = (
        df["net_flow"]
        .iloc[::-1]
        .rolling(window=horizon_days, min_periods=horizon_days)
        .sum()
        .iloc[::-1]
    )
    df["target"] = fwd_sum.values   # re-align after double-reverse

    # ------------------------------------------------------------------
    # Drop rows that cannot have a valid target (end of series) or that
    # lack enough history for the lag/rolling features.
    # ------------------------------------------------------------------
    # Row needs _MIN_HISTORY prior days → first valid row index = _MIN_HISTORY
    # (index 0 .. _MIN_HISTORY-1 have NaN lags/rolling).
    # Row needs horizon_days forward rows → last valid index = n - horizon_days
    # (index n-horizon_days+1 .. n-1 have NaN targets).
    valid_mask = df.index >= _MIN_HISTORY
    valid_mask &= df.index <= (n - horizon_days)

    df = df.loc[valid_mask].reset_index(drop=True)

    if df.empty:
        return _empty_table()

    feature_df = df[FEATURE_COLUMNS].copy()
    target_s   = df["target"].rename("target")
    full_df    = df[FEATURE_COLUMNS + ["date", "target"]].copy()

    return FeatureTable(features=feature_df, targets=target_s, full=full_df)


# ---------------------------------------------------------------------------
# Train / test split
# ---------------------------------------------------------------------------

def train_test_split_temporal(
    full_df: pd.DataFrame,
    test_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a feature table into chronological train and test sets.

    Parameters
    ----------
    full_df:
        The ``.full`` DataFrame from ``FeatureTable`` (must contain a ``date``
        column).  Assumed to be sorted by date ascending (guaranteed by
        ``build_feature_table``).
    test_fraction:
        Approximate fraction of rows reserved for the test set.  Default 0.2
        (last ~20 % of dates).

    Returns
    -------
    (train_df, test_df)
        Both DataFrames share the same columns as ``full_df``.  The split is
        strictly positional: **every train date is earlier than every test
        date**.  Never a random shuffle.

    Raises
    ------
    ValueError
        If ``full_df`` has fewer than 2 rows (can't split) or ``test_fraction``
        is not in (0, 1).
    """
    if not (0.0 < test_fraction < 1.0):
        raise ValueError(
            f"test_fraction must be in (0, 1), got {test_fraction}"
        )
    if len(full_df) < 2:
        raise ValueError(
            f"full_df has {len(full_df)} row(s); need at least 2 to split"
        )

    # Sort defensively — caller should already have a sorted frame.
    df = full_df.sort_values("date").reset_index(drop=True)

    n        = len(df)
    n_test   = max(1, round(n * test_fraction))
    n_train  = n - n_test          # at least 1 row in train (n >= 2, n_test >= 1)
    n_train  = max(1, n_train)     # belt-and-suspenders

    train_df = df.iloc[:n_train].reset_index(drop=True)
    test_df  = df.iloc[n_train:].reset_index(drop=True)

    return train_df, test_df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_table() -> FeatureTable:
    """Return a FeatureTable where every component is empty but typed correctly."""
    empty_feat = pd.DataFrame(columns=FEATURE_COLUMNS)
    empty_tgt  = pd.Series([], dtype=float, name="target")
    empty_full = pd.DataFrame(columns=FEATURE_COLUMNS + ["date", "target"])
    return FeatureTable(features=empty_feat, targets=empty_tgt, full=empty_full)
