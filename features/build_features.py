"""Feature engineering pipeline for F1 race-aware lap time prediction."""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from database.repository import F1Repository

logger = logging.getLogger(__name__)


def build_dataset(repository: Optional[F1Repository] = None) -> pd.DataFrame:
    """Build feature dataset from relational database with strict leakage prevention."""
    repo = repository or F1Repository()

    # 1. Fetch sessions
    sessions_df = repo.get_all_sessions()
    if sessions_df.empty:
        return pd.DataFrame()

    all_laps = []
    for _, session_row in sessions_df.iterrows():
        session_key = int(session_row["session_key"])
        circuit = session_row.get("circuit_short_name", "Unknown")

        laps = repo.get_laps(session_key)
        stints = repo.get_stints(session_key)
        weather = repo.get_weather(session_key)
        race_events = repo.get_race_events(session_key)

        if laps.empty or stints.empty:
            continue

        # Sort laps chronologically by driver and lap
        laps = laps.sort_values(by=["driver_number", "lap_number"]).copy()
        laps["circuit"] = circuit

        # 2. Map laps to tyre stints
        stint_map = []
        for _, lap in laps.iterrows():
            drv = lap["driver_number"]
            lap_num = lap["lap_number"]

            matching_stint = stints[
                (stints["driver_number"] == drv) & (stints["lap_start"] <= lap_num) & (lap_num <= stints["lap_end"])
            ]

            if not matching_stint.empty:
                s = matching_stint.iloc[0]
                compound = s["compound"]
                stint_num = s["stint_number"]
                tyre_age = s["tyre_age_at_start"] + (lap_num - s["lap_start"])
            else:
                compound = "UNKNOWN"
                stint_num = None
                tyre_age = None

            stint_map.append({"stint_number": stint_num, "compound": compound, "tyre_age": tyre_age})

        stint_df = pd.DataFrame(stint_map, index=laps.index)
        laps["stint_number"] = stint_df["stint_number"]
        laps["compound"] = stint_df["compound"]
        laps["tyre_age"] = stint_df["tyre_age"]

        # 3. Create strictly forward-shifted previous lap feature (leakage-safe)
        laps["previous_lap_time"] = laps.groupby("driver_number")["lap_duration"].shift(1)

        # 4. Integrate track temperature (align nearest observation or session mean)
        if not weather.empty and "track_temperature" in weather.columns:
            mean_track_temp = float(weather["track_temperature"].mean())
            mean_air_temp = float(weather["air_temperature"].mean())
        else:
            mean_track_temp = 35.0
            mean_air_temp = 25.0

        laps["track_temperature"] = mean_track_temp
        laps["air_temperature"] = mean_air_temp

        # 5. Data exclusions & filtering flags
        # Median lap per driver
        driver_medians = laps.groupby("driver_number")["lap_duration"].transform("median")
        laps["is_outlier"] = laps["lap_duration"] > (driver_medians * 1.12)
        laps["exclusion_reason"] = None

        laps.loc[laps["lap_duration"].isna(), "exclusion_reason"] = "missing_lap_time"
        laps.loc[laps["is_pit_out_lap"], "exclusion_reason"] = "pit_out_lap"
        laps.loc[laps["is_outlier"], "exclusion_reason"] = "slow_or_safety_car"
        laps.loc[laps["previous_lap_time"].isna(), "exclusion_reason"] = "first_lap_no_prior_feature"

        all_laps.append(laps)

    if not all_laps:
        return pd.DataFrame()

    full_df = pd.concat(all_laps, ignore_index=True)
    return full_df


def get_train_test_data(
    df: pd.DataFrame, holdout_session_key: int = 9157
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataset by complete session/race to eliminate leakage."""
    # Training mask: clean green-flag laps with no exclusion reason
    clean_mask = df["exclusion_reason"].isna()

    train_df = df[clean_mask & (df["session_key"] != holdout_session_key)].copy()
    test_df = df[clean_mask & (df["session_key"] == holdout_session_key)].copy()

    return train_df, test_df
