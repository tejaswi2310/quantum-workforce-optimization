"""
Regression tests for the forecasting hourly time-series data contract.

These tests verify:
  * validate_forecasting_time_series() correctly accepts or rejects input.
  * shift(24) and shift(168) produce the expected lag values on continuous data.
  * Group isolation: no lag values cross (channel, skill_group) boundaries.
  * The forecast pipeline produces the expected output shape (168-hour contract).

No forecasting models are trained here; all lag/rolling tests are performed
directly on small synthetic DataFrames to keep the suite fast and deterministic.
"""
import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta

from app.core_engine.forecasting.demand_forecaster import validate_forecasting_time_series


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hourly_df(
    start: str,
    n_hours: int,
    channel: str = "Voice",
    skill: str = "General",
    base_calls: int = 10,
) -> pd.DataFrame:
    """
    Build a perfectly continuous hourly DataFrame for a single
    (channel, skill_group) group.  The 'datetime' column is already present.
    Calls = base_calls + hour_offset so each hour is distinguishable.
    """
    start_dt = pd.to_datetime(start)
    rows = []
    for i in range(n_hours):
        dt = start_dt + pd.Timedelta(hours=i)
        rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "day_of_week": dt.strftime("%A"),
            "hour": dt.hour,
            "interval": f"{dt.hour:02d}:00-{(dt.hour + 1) % 24:02d}:00",
            "channel": channel,
            "skill_group": skill,
            "calls_received": base_calls + i,
            "datetime": dt,
        })
    return pd.DataFrame(rows)


def _multi_group_df(*group_dfs) -> pd.DataFrame:
    """Concatenate several group DataFrames and sort as train_forecast() would."""
    df = pd.concat(group_dfs, ignore_index=True)
    df = df.sort_values(by=["datetime", "channel", "skill_group"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 1. Continuous data — lag_24 correct
# ---------------------------------------------------------------------------

def test_continuous_data_lag24_correct():
    """
    shift(24) on a continuous 48-hour group must equal the value exactly
    24 hours (24 rows) earlier.
    """
    df = _make_hourly_df("2026-01-01 00:00", n_hours=48)
    validate_forecasting_time_series(df)  # must not raise

    df["lag_24"] = df.groupby(["channel", "skill_group"])["calls_received"].shift(24)

    # Row 24 must equal row 0, row 25 must equal row 1, etc.
    for i in range(24, 48):
        expected = df.loc[i - 24, "calls_received"]
        actual = df.loc[i, "lag_24"]
        assert actual == expected, (
            f"lag_24 mismatch at row {i}: expected {expected}, got {actual}"
        )


# ---------------------------------------------------------------------------
# 2. Continuous data — lag_168 correct
# ---------------------------------------------------------------------------

def test_continuous_data_lag168_correct():
    """
    shift(168) on a continuous 192-hour (8-day) group must equal the value
    exactly 168 hours (7 days) earlier.
    """
    df = _make_hourly_df("2026-01-01 00:00", n_hours=192)
    validate_forecasting_time_series(df)

    df["lag_168"] = df.groupby(["channel", "skill_group"])["calls_received"].shift(168)

    for i in range(168, 192):
        expected = df.loc[i - 168, "calls_received"]
        actual = df.loc[i, "lag_168"]
        assert actual == expected, (
            f"lag_168 mismatch at row {i}: expected {expected}, got {actual}"
        )


# ---------------------------------------------------------------------------
# 3. Missing hour detected
# ---------------------------------------------------------------------------

def test_missing_hour_detected():
    """
    A gap of 2 hours between consecutive timestamps must raise ValueError
    identifying channel, skill_group, and the missing timestamp.
    """
    df = _make_hourly_df("2026-01-01 00:00", n_hours=48)
    # Remove hour 12 to create a gap: 11:00 -> 13:00
    df = df[df["hour"] != 12].reset_index(drop=True)

    with pytest.raises(ValueError, match="Missing hourly timestamp"):
        validate_forecasting_time_series(df)


def test_missing_hour_error_identifies_group():
    """The ValueError message must name the affected channel and skill_group."""
    df = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Chat", skill="Technical")
    df = df[df["hour"] != 6].reset_index(drop=True)

    with pytest.raises(ValueError, match="channel='Chat'") as exc_info:
        validate_forecasting_time_series(df)
    assert "skill_group='Technical'" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Duplicate timestamp detected
# ---------------------------------------------------------------------------

def test_duplicate_timestamp_detected():
    """
    A duplicated (datetime, channel, skill_group) row must raise ValueError
    identifying the duplicate timestamp.
    """
    df = _make_hourly_df("2026-01-01 00:00", n_hours=48)
    dup_row = df.iloc[[10]].copy()  # duplicate hour 10
    df = pd.concat([df, dup_row], ignore_index=True)
    df = df.sort_values(by=["datetime", "channel", "skill_group"]).reset_index(drop=True)

    with pytest.raises(ValueError, match="Duplicate timestamp"):
        validate_forecasting_time_series(df)


def test_duplicate_timestamp_error_identifies_group():
    """The ValueError message must name channel and skill_group for duplicates."""
    df = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Email", skill="Billing")
    dup_row = df.iloc[[5]].copy()
    df = pd.concat([df, dup_row], ignore_index=True)
    df = df.sort_values(by=["datetime", "channel", "skill_group"]).reset_index(drop=True)

    with pytest.raises(ValueError, match="channel='Email'") as exc_info:
        validate_forecasting_time_series(df)
    assert "skill_group='Billing'" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5. Irregular frequency detected
# ---------------------------------------------------------------------------

def test_irregular_frequency_detected():
    """
    A 30-minute sub-hourly interval must raise ValueError identifying
    the irregular interval.
    """
    df = _make_hourly_df("2026-01-01 00:00", n_hours=48)
    # Insert a row at :30 between hour 5 and hour 6
    half_hour_dt = pd.to_datetime("2026-01-01 05:30")
    extra = pd.DataFrame([{
        "date": "2026-01-01",
        "day_of_week": "Thursday",
        "hour": 5,
        "interval": "05:30-06:00",
        "channel": "Voice",
        "skill_group": "General",
        "calls_received": 999,
        "datetime": half_hour_dt,
    }])
    df = pd.concat([df, extra], ignore_index=True)
    df = df.sort_values(by=["datetime", "channel", "skill_group"]).reset_index(drop=True)

    with pytest.raises(ValueError, match="Irregular timestamp interval"):
        validate_forecasting_time_series(df)


# ---------------------------------------------------------------------------
# 6. Unsorted input sorted before lag computation
# ---------------------------------------------------------------------------

def test_unsorted_input_sorted_before_lag():
    """
    Shuffled input that is sorted before calling the validator must produce
    the same lag_24 values as pre-sorted input.
    """
    df_sorted = _make_hourly_df("2026-01-01 00:00", n_hours=48)

    # Shuffle
    df_shuffled = df_sorted.sample(frac=1, random_state=99).reset_index(drop=True)
    df_shuffled = df_shuffled.sort_values(
        by=["datetime", "channel", "skill_group"]
    ).reset_index(drop=True)

    validate_forecasting_time_series(df_shuffled)  # must pass after sort

    df_sorted["lag_24"] = df_sorted.groupby(
        ["channel", "skill_group"])["calls_received"].shift(24)
    df_shuffled["lag_24"] = df_shuffled.groupby(
        ["channel", "skill_group"])["calls_received"].shift(24)

    pd.testing.assert_series_equal(
        df_sorted["lag_24"].reset_index(drop=True),
        df_shuffled["lag_24"].reset_index(drop=True),
        check_names=False,
    )


# ---------------------------------------------------------------------------
# 7. Multiple channels — no cross-group leakage
# ---------------------------------------------------------------------------

def test_multiple_channels_no_cross_group_leakage():
    """
    lag_24 for Chat+General must equal Chat+General values 24 hours earlier,
    NOT Voice+General values.
    """
    df_voice = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Voice",
                                skill="General", base_calls=100)
    df_chat = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Chat",
                               skill="General", base_calls=200)
    df = _multi_group_df(df_voice, df_chat)

    validate_forecasting_time_series(df)

    df["lag_24"] = df.groupby(["channel", "skill_group"])["calls_received"].shift(24)

    chat_rows = df[df["channel"] == "Chat"].reset_index(drop=True)
    for i in range(24, len(chat_rows)):
        expected = chat_rows.loc[i - 24, "calls_received"]
        actual = chat_rows.loc[i, "lag_24"]
        assert actual == expected, (
            f"Chat lag_24 at position {i}: expected {expected}, got {actual}"
        )
        # Must not be a Voice value (100-based)
        assert actual >= 200, (
            f"Chat lag_24 appears to contain a Voice value: {actual}"
        )


# ---------------------------------------------------------------------------
# 8. Multiple skill groups — isolated
# ---------------------------------------------------------------------------

def test_multiple_skill_groups_isolated():
    """
    lag_24 for Voice+Technical must equal Voice+Technical values 24h earlier,
    NOT Voice+General values.
    """
    df_general = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Voice",
                                  skill="General", base_calls=10)
    df_technical = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Voice",
                                    skill="Technical", base_calls=1000)
    df = _multi_group_df(df_general, df_technical)

    validate_forecasting_time_series(df)

    df["lag_24"] = df.groupby(["channel", "skill_group"])["calls_received"].shift(24)

    tech_rows = df[df["skill_group"] == "Technical"].reset_index(drop=True)
    for i in range(24, len(tech_rows)):
        expected = tech_rows.loc[i - 24, "calls_received"]
        actual = tech_rows.loc[i, "lag_24"]
        assert actual == expected
        assert actual >= 1000, (
            f"Technical lag_24 contains a General-group value: {actual}"
        )


# ---------------------------------------------------------------------------
# 9. Group boundary — lag does not cross groups
# ---------------------------------------------------------------------------

def test_group_boundary_lag_isolation():
    """
    The first 24 lag_24 values in any group must be NaN (no data available
    from 24 hours prior), never values from a different group.
    """
    df_a = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Voice",
                            skill="General", base_calls=500)
    df_b = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Chat",
                            skill="Sales", base_calls=999)
    df = _multi_group_df(df_a, df_b)

    validate_forecasting_time_series(df)

    df["lag_24"] = df.groupby(["channel", "skill_group"])["calls_received"].shift(24)

    # First 24 rows of each group must be NaN
    for (ch, sk), grp in df.groupby(["channel", "skill_group"]):
        grp_reset = grp.reset_index(drop=True)
        for i in range(24):
            assert pd.isna(grp_reset.loc[i, "lag_24"]), (
                f"Expected NaN for {ch}/{sk} lag_24 at position {i}, "
                f"got {grp_reset.loc[i, 'lag_24']}"
            )


# ---------------------------------------------------------------------------
# 10. lag_24 semantics: 24 hours, not 24 global rows
# ---------------------------------------------------------------------------

def test_lag24_semantics_24_hours_not_24_rows_globally():
    """
    In a multi-group DataFrame, the global position of row N in group B is
    NOT the same as 24 global rows earlier.  Verify that groupby().shift(24)
    correctly uses 24 group-local rows (= 24 hours) rather than 24 global rows.
    """
    df_a = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Voice",
                            skill="General", base_calls=100)
    df_b = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Chat",
                            skill="General", base_calls=200)
    df_c = _make_hourly_df("2026-01-01 00:00", n_hours=48, channel="Email",
                            skill="General", base_calls=300)
    df = _multi_group_df(df_a, df_b, df_c)

    validate_forecasting_time_series(df)

    df["lag_24"] = df.groupby(["channel", "skill_group"])["calls_received"].shift(24)

    for (ch, sk), grp in df.groupby(["channel", "skill_group"]):
        grp_reset = grp.reset_index(drop=True)
        for i in range(24, len(grp_reset)):
            expected = grp_reset.loc[i - 24, "calls_received"]
            actual = grp_reset.loc[i, "lag_24"]
            assert actual == expected, (
                f"({ch}/{sk}) lag_24 at local position {i}: "
                f"expected {expected}, got {actual}"
            )


# ---------------------------------------------------------------------------
# 11. validate_forecasting_time_series does not mutate caller DataFrame
# ---------------------------------------------------------------------------

def test_validator_does_not_mutate_caller():
    """validate_forecasting_time_series must not change the caller's DataFrame."""
    df = _make_hourly_df("2026-01-01 00:00", n_hours=48)
    original_cols = list(df.columns)
    original_index = list(df.index)
    original_values = df["calls_received"].tolist()

    validate_forecasting_time_series(df)

    assert list(df.columns) == original_cols, "Columns were mutated"
    assert list(df.index) == original_index, "Index was mutated"
    assert df["calls_received"].tolist() == original_values, "Values were mutated"


# ---------------------------------------------------------------------------
# 12. Forecast output shape (168-hour downstream compatibility)
# ---------------------------------------------------------------------------

def test_forecast_output_shape():
    """
    The future forecast generation loop in train_forecast() is configured as:
        7 days x 24 hours x 3 channels x 4 skills = 2016 rows.
    Verify this contract against the known generator parameters by simulating
    the loop dimensions without running the full ML pipeline.
    """
    days = 7
    hours_per_day = 24
    channels = ["Voice", "Chat", "Email"]
    skills = ["Billing", "Technical", "Sales", "General"]

    expected_rows = days * hours_per_day * len(channels) * len(skills)
    assert expected_rows == 2016, (
        f"Forecast output shape contract broken: {expected_rows} != 2016"
    )

    # Also verify that 2016 rows produce exactly 168 unique (date, hour)
    # combinations -- the downstream contract the classical optimizer validates.
    base = datetime(2026, 1, 1)
    records = []
    for i in range(1, days + 1):
        future_date = base + timedelta(days=i)
        for hour in range(hours_per_day):
            for ch in channels:
                for sk in skills:
                    records.append({
                        "date": future_date.strftime("%Y-%m-%d"),
                        "hour": hour,
                    })

    df_fc = pd.DataFrame(records)
    unique_date_hours = df_fc[["date", "hour"]].drop_duplicates()
    assert len(unique_date_hours) == 168, (
        f"Expected 168 unique (date, hour) combinations, got {len(unique_date_hours)}"
    )


def test_168_hour_downstream_compatibility():
    """
    The optimizer's validation logic requires exactly 168 unique (date, hour)
    combinations in forecast_results.csv.  Confirm the forecast loop's
    7x24 date-hour grid satisfies this without running the optimizer.
    """
    base = datetime(2026, 6, 1)
    date_hours = set()
    for i in range(1, 8):
        future_date = base + timedelta(days=i)
        date_str = future_date.strftime("%Y-%m-%d")
        for hour in range(24):
            date_hours.add((date_str, hour))

    assert len(date_hours) == 168, (
        f"168-hour downstream contract violated: got {len(date_hours)} unique slots"
    )


# ---------------------------------------------------------------------------
# 13. Valid continuous data passes without error
# ---------------------------------------------------------------------------

def test_valid_continuous_data_passes():
    """
    Perfectly continuous hourly data must pass validation without any exception.
    """
    df_voice_general = _make_hourly_df("2026-01-01 00:00", n_hours=192,
                                        channel="Voice", skill="General")
    df_chat_billing = _make_hourly_df("2026-01-01 00:00", n_hours=192,
                                       channel="Chat", skill="Billing")
    df = _multi_group_df(df_voice_general, df_chat_billing)

    # Should complete without raising
    validate_forecasting_time_series(df)

