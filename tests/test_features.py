"""
Unit tests for backend/ml/features.py

Covers
------
1.  Lag correctness — lag_1/3/7/14 values match the hand-built series exactly.
2.  Rolling features — rolling_mean_7/14 and rolling_std_7 are correct.
3.  day_of_week — correct weekday integer for known dates.
4.  n_events_lag_7 — sums the right trailing window.
5.  Target correctness — target equals the sum of net_flow over [t, t+horizon).
6.  No lookahead — no row has a target that reaches past the last data day.
7.  Minimum-history guard — rows with fewer than 14 prior days are absent.
8.  Chronological split — max(train date) < min(test date); no overlap.
9.  Split fractions — test set is ~20 % of rows (±1 row tolerance).
10. Empty / too-small inputs — build_feature_table returns an empty FeatureTable
    without raising when the input has fewer rows than MIN_HISTORY + horizon.
11. FEATURE_COLUMNS order — the feature DataFrame columns match the declared
    constant exactly.
12. train_test_split_temporal raises on bad inputs.
13. horizon_days=1 edge case — target equals net_flow of day t itself.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_daily(n: int, start: date = date(2024, 1, 1), base_flow: float = 1000.0) -> pd.DataFrame:
    """Return a deterministic gapless daily_df with n rows.

    net_flow on day i = base_flow * (i + 1)  so every value is distinct and
    lags are easy to verify by hand.
    n_events on day i = i + 1.
    """
    dates = [start + timedelta(days=i) for i in range(n)]
    flows = [base_flow * (i + 1) for i in range(n)]
    events = [i + 1 for i in range(n)]
    return pd.DataFrame({"date": dates, "net_flow": flows, "n_events": events})


def _build(n: int = 40, horizon: int = 7, **kw) -> object:
    """Convenience: make a daily_df and call build_feature_table."""
    from backend.ml.features import build_feature_table
    df = _make_daily(n, **kw)
    return build_feature_table(df, horizon_days=horizon)


# ---------------------------------------------------------------------------
# 1. Lag correctness
# ---------------------------------------------------------------------------

class TestLagValues:
    """Lag features must equal net_flow at the correct historical offset."""

    def _ft(self):
        return _build(n=40, horizon=7)

    def _daily(self):
        return _make_daily(40)

    def test_lag_1_first_valid_row(self):
        ft = self._ft()
        daily = self._daily()
        # First row in the feature table corresponds to index 14 of daily_df.
        # lag_1 at that row = net_flow[13].
        row = ft.full.iloc[0]
        expected = daily["net_flow"].iloc[13]
        assert row["lag_1"] == pytest.approx(expected)

    def test_lag_3_first_valid_row(self):
        ft = self._ft()
        daily = self._daily()
        row = ft.full.iloc[0]
        expected = daily["net_flow"].iloc[11]   # index 14 - 3 = 11
        assert row["lag_3"] == pytest.approx(expected)

    def test_lag_7_first_valid_row(self):
        ft = self._ft()
        daily = self._daily()
        row = ft.full.iloc[0]
        expected = daily["net_flow"].iloc[7]    # index 14 - 7 = 7
        assert row["lag_7"] == pytest.approx(expected)

    def test_lag_14_first_valid_row(self):
        ft = self._ft()
        daily = self._daily()
        row = ft.full.iloc[0]
        expected = daily["net_flow"].iloc[0]    # index 14 - 14 = 0
        assert row["lag_14"] == pytest.approx(expected)

    def test_lag_1_mid_series(self):
        """Spot-check lag_1 at a later row to confirm consistent offset."""
        ft = self._ft()
        daily = self._daily()
        # Second feature row = daily index 15; lag_1 = daily[14]
        row = ft.full.iloc[1]
        expected = daily["net_flow"].iloc[14]
        assert row["lag_1"] == pytest.approx(expected)

    def test_lag_values_all_distinct(self):
        """Since net_flow is strictly increasing all four lags must differ."""
        row = _build(n=40).full.iloc[0]
        lags = [row["lag_1"], row["lag_3"], row["lag_7"], row["lag_14"]]
        assert len(set(lags)) == 4


# ---------------------------------------------------------------------------
# 2. Rolling features
# ---------------------------------------------------------------------------

class TestRollingFeatures:
    """rolling_mean and rolling_std use strictly-past data (no current row)."""

    def _daily_and_ft(self):
        daily = _make_daily(40)
        from backend.ml.features import build_feature_table
        ft = build_feature_table(daily, horizon_days=7)
        return daily, ft

    def test_rolling_mean_7_first_row(self):
        """rolling_mean_7 at first feature row = mean of daily[7..13] (7 values)."""
        daily, ft = self._daily_and_ft()
        expected = daily["net_flow"].iloc[7:14].mean()
        assert ft.full.iloc[0]["rolling_mean_7"] == pytest.approx(expected)

    def test_rolling_mean_14_first_row(self):
        """rolling_mean_14 at first feature row = mean of daily[0..13] (14 values)."""
        daily, ft = self._daily_and_ft()
        expected = daily["net_flow"].iloc[0:14].mean()
        assert ft.full.iloc[0]["rolling_mean_14"] == pytest.approx(expected)

    def test_rolling_std_7_first_row(self):
        """rolling_std_7 at first feature row = std of daily[7..13]."""
        daily, ft = self._daily_and_ft()
        expected = daily["net_flow"].iloc[7:14].std()
        assert ft.full.iloc[0]["rolling_std_7"] == pytest.approx(expected)

    def test_rolling_mean_7_no_current_row_contamination(self):
        """rolling_mean_7 must not include net_flow[t] — verified by using a
        series where net_flow[t] is a large outlier."""
        from backend.ml.features import build_feature_table
        # Build a 22-row series where the 15th day (first feature row, index=14)
        # has a huge spike. rolling_mean_7 must NOT include it.
        daily = _make_daily(22)
        daily.loc[14, "net_flow"] = 1_000_000.0
        ft = build_feature_table(daily, horizon_days=7)
        # mean of the 7 days *before* index 14: indices [7..13]
        expected = daily["net_flow"].iloc[7:14].mean()
        assert ft.full.iloc[0]["rolling_mean_7"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 3. day_of_week
# ---------------------------------------------------------------------------

class TestDayOfWeek:
    def test_known_monday(self):
        """2024-01-01 is a Monday → day_of_week == 0."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(40, start=date(2024, 1, 1))
        ft = build_feature_table(daily, horizon_days=7)
        # First feature row = date 2024-01-15 (index 14), which is a Monday.
        assert date(2024, 1, 15).weekday() == 0  # self-check
        assert ft.full.iloc[0]["day_of_week"] == 0

    def test_known_sunday(self):
        """2024-01-21 is a Sunday → day_of_week == 6."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(40, start=date(2024, 1, 1))
        ft = build_feature_table(daily, horizon_days=7)
        # 2024-01-21 = index 20 in daily → feature-table index 20-14 = 6
        assert date(2024, 1, 21).weekday() == 6  # self-check
        assert ft.full.iloc[6]["day_of_week"] == 6

    def test_day_of_week_range(self):
        """All day_of_week values must be in [0, 6]."""
        ft = _build(n=40)
        assert ft.features["day_of_week"].between(0, 6).all()


# ---------------------------------------------------------------------------
# 4. n_events_lag_7
# ---------------------------------------------------------------------------

class TestNEventsLag7:
    def test_n_events_lag7_first_row(self):
        """n_events_lag_7 at first feature row = sum of n_events[7..13]."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(40)
        ft = build_feature_table(daily, horizon_days=7)
        expected = int(daily["n_events"].iloc[7:14].sum())
        assert ft.full.iloc[0]["n_events_lag_7"] == pytest.approx(expected)

    def test_n_events_lag7_does_not_include_current_row(self):
        """Spike on the current day must not appear in n_events_lag_7."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(22)
        daily.loc[14, "n_events"] = 9999
        ft = build_feature_table(daily, horizon_days=7)
        expected = int(daily["n_events"].iloc[7:14].sum())
        assert ft.full.iloc[0]["n_events_lag_7"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# 5. Target correctness
# ---------------------------------------------------------------------------

class TestTargetValues:
    """target = sum of net_flow over [t, t+horizon_days)."""

    def test_target_horizon_7_first_row(self):
        """target at first feature row = sum of net_flow[14..20] (7 values)."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(40)
        ft = build_feature_table(daily, horizon_days=7)
        expected = daily["net_flow"].iloc[14:21].sum()
        assert ft.full.iloc[0]["target"] == pytest.approx(expected)

    def test_target_horizon_1_equals_own_flow(self):
        """With horizon=1 the target must equal the day's own net_flow."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(30)
        ft = build_feature_table(daily, horizon_days=1)
        # First feature row = daily index 14
        expected = daily["net_flow"].iloc[14]
        assert ft.full.iloc[0]["target"] == pytest.approx(expected)

    def test_target_horizon_14(self):
        """target with horizon=14 sums 14 days starting at t."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(50)
        ft = build_feature_table(daily, horizon_days=14)
        expected = daily["net_flow"].iloc[14:28].sum()
        assert ft.full.iloc[0]["target"] == pytest.approx(expected)

    def test_target_is_aligned_with_features(self):
        """targets Series and features DataFrame must have matching indices."""
        ft = _build(n=40)
        assert list(ft.targets.index) == list(ft.features.index)


# ---------------------------------------------------------------------------
# 6. No lookahead — target never reaches past the last data day
# ---------------------------------------------------------------------------

class TestNoLookahead:
    """No row in the feature table should require future data beyond the series."""

    def _check_no_lookahead(self, n: int, horizon: int) -> None:
        from backend.ml.features import build_feature_table
        daily = _make_daily(n)
        ft = build_feature_table(daily, horizon_days=horizon)
        if ft.full.empty:
            return  # nothing to check
        last_data_day = daily["date"].max()
        for _, row in ft.full.iterrows():
            row_date = row["date"]
            # The target window ends at row_date + horizon_days - 1 (inclusive)
            last_needed = row_date + timedelta(days=horizon - 1)
            assert last_needed <= last_data_day, (
                f"Row date {row_date}: target window ends {last_needed} "
                f"but last data day is {last_data_day}"
            )

    def test_no_lookahead_horizon_7(self):
        self._check_no_lookahead(n=40, horizon=7)

    def test_no_lookahead_horizon_14(self):
        self._check_no_lookahead(n=50, horizon=14)

    def test_no_lookahead_horizon_1(self):
        self._check_no_lookahead(n=30, horizon=1)

    def test_last_row_date_plus_horizon_within_data(self):
        """The last feature row's date + horizon - 1 must equal the last data day."""
        from backend.ml.features import build_feature_table
        n, horizon = 40, 7
        daily = _make_daily(n)
        ft = build_feature_table(daily, horizon_days=horizon)
        last_feature_date = ft.full["date"].max()
        last_data_day     = daily["date"].max()
        assert last_feature_date + timedelta(days=horizon - 1) == last_data_day

    def test_row_count_exact(self):
        """Number of rows = n - _MIN_HISTORY - horizon_days + 1."""
        from backend.ml.features import build_feature_table, _MIN_HISTORY
        n, horizon = 40, 7
        daily = _make_daily(n)
        ft = build_feature_table(daily, horizon_days=horizon)
        expected = n - _MIN_HISTORY - horizon + 1
        assert len(ft.full) == expected


# ---------------------------------------------------------------------------
# 7. Minimum-history guard
# ---------------------------------------------------------------------------

class TestMinHistoryGuard:
    """Rows at positions < _MIN_HISTORY must never appear in the output."""

    def test_first_feature_date(self):
        """The first feature row must be exactly _MIN_HISTORY days after the
        first data day."""
        from backend.ml.features import build_feature_table, _MIN_HISTORY
        start = date(2024, 3, 1)
        daily = _make_daily(40, start=start)
        ft = build_feature_table(daily, horizon_days=7)
        expected_first = start + timedelta(days=_MIN_HISTORY)
        assert ft.full["date"].min() == expected_first

    def test_no_nan_in_features(self):
        """All cells in the feature matrix must be finite numbers (no NaN)."""
        ft = _build(n=40)
        assert not ft.features.isnull().any().any()

    def test_no_nan_in_targets(self):
        ft = _build(n=40)
        assert not ft.targets.isnull().any()


# ---------------------------------------------------------------------------
# 8 & 9. Chronological split — order and fractions
# ---------------------------------------------------------------------------

class TestChronologicalSplit:
    """train_test_split_temporal must preserve date order and never overlap."""

    def _split(self, n: int = 40, horizon: int = 7, fraction: float = 0.2):
        from backend.ml.features import build_feature_table, train_test_split_temporal
        daily = _make_daily(n)
        ft = build_feature_table(daily, horizon_days=horizon)
        return train_test_split_temporal(ft.full, test_fraction=fraction)

    def test_no_date_overlap(self):
        train, test = self._split()
        train_dates = set(train["date"])
        test_dates  = set(test["date"])
        assert train_dates.isdisjoint(test_dates), "Train and test dates overlap"

    def test_strictly_chronological(self):
        """Every train date must precede every test date."""
        train, test = self._split()
        assert train["date"].max() < test["date"].min()

    def test_train_dates_sorted(self):
        train, _ = self._split()
        dates = list(train["date"])
        assert dates == sorted(dates)

    def test_test_dates_sorted(self):
        _, test = self._split()
        dates = list(test["date"])
        assert dates == sorted(dates)

    def test_all_rows_accounted_for(self):
        """train + test row count must equal the full feature-table row count."""
        from backend.ml.features import build_feature_table, train_test_split_temporal
        daily = _make_daily(40)
        from backend.ml.features import build_feature_table
        ft = build_feature_table(daily, horizon_days=7)
        train, test = train_test_split_temporal(ft.full)
        assert len(train) + len(test) == len(ft.full)

    def test_test_fraction_approx_20_pct(self):
        """Test set must be within 1 row of 20 % of the total."""
        from backend.ml.features import build_feature_table, train_test_split_temporal
        daily = _make_daily(40)
        ft = build_feature_table(daily, horizon_days=7)
        total = len(ft.full)
        _, test = train_test_split_temporal(ft.full, test_fraction=0.2)
        expected = round(total * 0.2)
        assert abs(len(test) - expected) <= 1

    def test_custom_fraction(self):
        """A non-default fraction should produce the right test size (±1)."""
        from backend.ml.features import build_feature_table, train_test_split_temporal
        daily = _make_daily(50)
        ft = build_feature_table(daily, horizon_days=7)
        total = len(ft.full)
        _, test = train_test_split_temporal(ft.full, test_fraction=0.3)
        expected = round(total * 0.3)
        assert abs(len(test) - expected) <= 1

    def test_split_preserves_columns(self):
        """Train and test DataFrames must have the same columns as full_df."""
        from backend.ml.features import build_feature_table, train_test_split_temporal
        daily = _make_daily(40)
        ft = build_feature_table(daily, horizon_days=7)
        train, test = train_test_split_temporal(ft.full)
        assert list(train.columns) == list(ft.full.columns)
        assert list(test.columns)  == list(ft.full.columns)


# ---------------------------------------------------------------------------
# 10. Empty / too-small inputs
# ---------------------------------------------------------------------------

class TestSmallInputs:
    """build_feature_table must return an empty FeatureTable without raising."""

    def _empty_ft(self, ft) -> bool:
        return ft.features.empty and ft.targets.empty and ft.full.empty

    def test_empty_dataframe(self):
        from backend.ml.features import build_feature_table
        daily = pd.DataFrame(columns=["date", "net_flow", "n_events"])
        ft = build_feature_table(daily)
        assert self._empty_ft(ft)

    def test_too_few_rows_for_history(self):
        """10 rows < _MIN_HISTORY=14 → empty result."""
        from backend.ml.features import build_feature_table
        ft = build_feature_table(_make_daily(10))
        assert self._empty_ft(ft)

    def test_exactly_min_history_no_horizon(self):
        """14 rows: history filled but zero rows survive after horizon drop."""
        from backend.ml.features import build_feature_table
        # With n=14, horizon=7: n - 14 - 7 + 1 = -6 → empty
        ft = build_feature_table(_make_daily(14), horizon_days=7)
        assert self._empty_ft(ft)

    def test_minimum_viable_input(self):
        """n = _MIN_HISTORY + horizon gives exactly 1 feature row."""
        from backend.ml.features import build_feature_table, _MIN_HISTORY
        horizon = 7
        n = _MIN_HISTORY + horizon  # = 21
        ft = build_feature_table(_make_daily(n), horizon_days=horizon)
        assert len(ft.full) == 1

    def test_empty_result_columns(self):
        """Even an empty FeatureTable must carry the correct column names."""
        from backend.ml.features import build_feature_table, FEATURE_COLUMNS
        ft = build_feature_table(_make_daily(5))
        assert list(ft.features.columns) == FEATURE_COLUMNS
        assert "target" in ft.full.columns

    def test_bad_horizon_raises(self):
        from backend.ml.features import build_feature_table
        with pytest.raises(ValueError, match="horizon_days"):
            build_feature_table(_make_daily(30), horizon_days=0)

    def test_missing_columns_raises(self):
        from backend.ml.features import build_feature_table
        bad = pd.DataFrame({"date": [], "net_flow": []})   # missing n_events
        with pytest.raises(ValueError, match="missing columns"):
            build_feature_table(bad)


# ---------------------------------------------------------------------------
# 11. FEATURE_COLUMNS order
# ---------------------------------------------------------------------------

class TestFeatureColumnsOrder:
    def test_columns_match_constant(self):
        from backend.ml.features import build_feature_table, FEATURE_COLUMNS
        ft = build_feature_table(_make_daily(40))
        assert list(ft.features.columns) == FEATURE_COLUMNS

    def test_full_df_has_date_and_target(self):
        from backend.ml.features import build_feature_table, FEATURE_COLUMNS
        ft = build_feature_table(_make_daily(40))
        assert "date"   in ft.full.columns
        assert "target" in ft.full.columns

    def test_features_does_not_contain_target(self):
        ft = _build(n=40)
        assert "target" not in ft.features.columns

    def test_features_does_not_contain_date(self):
        ft = _build(n=40)
        assert "date" not in ft.features.columns


# ---------------------------------------------------------------------------
# 12. train_test_split_temporal raises on bad inputs
# ---------------------------------------------------------------------------

class TestSplitValidation:
    def _full(self):
        from backend.ml.features import build_feature_table
        return build_feature_table(_make_daily(40)).full

    def test_fraction_zero_raises(self):
        from backend.ml.features import train_test_split_temporal
        with pytest.raises(ValueError, match="test_fraction"):
            train_test_split_temporal(self._full(), test_fraction=0.0)

    def test_fraction_one_raises(self):
        from backend.ml.features import train_test_split_temporal
        with pytest.raises(ValueError, match="test_fraction"):
            train_test_split_temporal(self._full(), test_fraction=1.0)

    def test_single_row_raises(self):
        from backend.ml.features import train_test_split_temporal
        single = self._full().iloc[:1].copy()
        with pytest.raises(ValueError):
            train_test_split_temporal(single)


# ---------------------------------------------------------------------------
# 13. horizon_days=1 edge case
# ---------------------------------------------------------------------------

class TestHorizonOne:
    def test_target_equals_own_net_flow(self):
        """With horizon=1 every target must equal the net_flow for that day."""
        from backend.ml.features import build_feature_table
        daily = _make_daily(30)
        ft = build_feature_table(daily, horizon_days=1)
        # Merge on date to compare target vs net_flow
        merged = ft.full.merge(daily, on="date", how="left")
        for _, row in merged.iterrows():
            assert row["target"] == pytest.approx(row["net_flow"])

    def test_row_count_horizon_1(self):
        """With horizon=1 the last data day itself is a valid feature row."""
        from backend.ml.features import build_feature_table, _MIN_HISTORY
        n = 30
        ft = build_feature_table(_make_daily(n), horizon_days=1)
        # n - _MIN_HISTORY - 1 + 1 = n - _MIN_HISTORY
        assert len(ft.full) == n - _MIN_HISTORY
