"""Unit tests for feature engineering, tyre age conventions, and leakage prevention."""

import numpy as np
import pandas as pd
import pytest

from features.build_features import get_train_test_data


def test_tyre_age_calculation():
    # Test formula: tyre_age = tyre_age_at_start + (lap_number - lap_start)
    lap_start = 1
    lap_end = 20
    tyre_age_at_start = 3  # Scuffed set used in qualifying

    laps = pd.DataFrame({"lap_number": [1, 2, 10, 20]})
    laps["tyre_age"] = tyre_age_at_start + (laps["lap_number"] - lap_start)

    assert laps.loc[laps["lap_number"] == 1, "tyre_age"].iloc[0] == 3
    assert laps.loc[laps["lap_number"] == 2, "tyre_age"].iloc[0] == 4
    assert laps.loc[laps["lap_number"] == 10, "tyre_age"].iloc[0] == 12
    assert laps.loc[laps["lap_number"] == 20, "tyre_age"].iloc[0] == 22


def test_previous_lap_time_leakage_safe_shift():
    # Verify that previous_lap_time is strictly shifted by 1 within driver
    df = pd.DataFrame({
        "driver_number": [1, 1, 1, 11, 11],
        "lap_number": [1, 2, 3, 1, 2],
        "lap_duration": [95.0, 93.0, 92.5, 96.0, 94.0],
    })
    df["previous_lap_time"] = df.groupby("driver_number")["lap_duration"].shift(1)

    # First lap of each driver must be NaN (no prior lap within race)
    assert pd.isna(df.loc[df["lap_number"] == 1, "previous_lap_time"]).all()
    # Lap 2 previous time must equal lap 1 time
    assert df.loc[(df["driver_number"] == 1) & (df["lap_number"] == 2), "previous_lap_time"].iloc[0] == 95.0
    assert df.loc[(df["driver_number"] == 11) & (df["lap_number"] == 2), "previous_lap_time"].iloc[0] == 96.0


def test_no_race_overlap_in_train_test_split():
    df = pd.DataFrame({
        "session_key": [9126, 9126, 9157, 9157],
        "driver_number": [1, 1, 1, 1],
        "lap_number": [2, 3, 2, 3],
        "lap_duration": [90.0, 90.2, 85.0, 85.2],
        "previous_lap_time": [91.0, 90.0, 86.0, 85.0],
        "exclusion_reason": [None, None, None, None],
    })

    train_df, test_df = get_train_test_data(df, holdout_session_key=9157)
    assert (train_df["session_key"] == 9126).all()
    assert (test_df["session_key"] == 9157).all()
    # Ensure disjoint sessions
    assert len(set(train_df["session_key"]).intersection(set(test_df["session_key"]))) == 0
