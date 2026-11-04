"""Unit tests for data normalization and validation rules."""

import pandas as pd
import pytest

from ingestion.normalize import (
    normalize_drivers,
    normalize_laps,
    normalize_stints,
    normalize_telemetry,
    parse_timestamp_utc,
)
from ingestion.validate import DataValidator


def test_parse_timestamp_utc():
    ts = "2023-03-05T15:00:00+00:00"
    parsed = parse_timestamp_utc(ts)
    assert parsed.startswith("2023-03-05")
    assert parse_timestamp_utc(None) is None
    assert parse_timestamp_utc("") is None


def test_normalize_laps_preserves_nulls():
    raw_laps = [
        {
            "session_key": 9158,
            "driver_number": 1,
            "lap_number": 1,
            "lap_duration": 96.54,
            "duration_sector_1": 31.2,
            "duration_sector_2": 39.8,
            "duration_sector_3": 25.54,
            "is_pit_out_lap": False,
        },
        {
            "session_key": 9158,
            "driver_number": 1,
            "lap_number": 2,
            "lap_duration": None,  # Incomplete / deleted lap time
            "duration_sector_1": 31.1,
            "duration_sector_2": None,
            "duration_sector_3": None,
            "is_pit_out_lap": False,
        },
    ]

    df = normalize_laps(raw_laps)
    assert len(df) == 2
    assert df.loc[df["lap_number"] == 1, "lap_duration"].iloc[0] == 96.54
    # Ensure missing lap time is preserved as NaN, not silently converted to 0
    assert pd.isna(df.loc[df["lap_number"] == 2, "lap_duration"].iloc[0])


def test_normalize_telemetry_preserves_sensor_nulls():
    raw_telemetry = [
        {"session_key": 9158, "driver_number": 1, "date": "2023-03-05T15:05:00Z", "speed": 290.5, "throttle": 100},
        {"session_key": 9158, "driver_number": 1, "date": "2023-03-05T15:05:01Z", "speed": None, "throttle": None},
    ]
    df = normalize_telemetry(raw_telemetry)
    assert len(df) == 2
    assert pd.isna(df.iloc[1]["speed"])
    assert pd.isna(df.iloc[1]["throttle"])


def test_validate_lap_to_stint_mapping():
    laps_df = pd.DataFrame([
        {"session_key": 9158, "driver_number": 1, "lap_number": 1},
        {"session_key": 9158, "driver_number": 1, "lap_number": 15},
        {"session_key": 9158, "driver_number": 1, "lap_number": 16},
    ])

    stints_df = pd.DataFrame([
        {"session_key": 9158, "driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 15},
        {"session_key": 9158, "driver_number": 1, "stint_number": 2, "lap_start": 16, "lap_end": 35},
    ])

    audit = DataValidator.validate_lap_to_stint_mapping(laps_df, stints_df)
    assert audit["valid"] is True
    assert audit["multi_mapped_laps"] == 0
    assert audit["unmapped_laps"] == 0


def test_validate_lap_to_stint_detects_multiple_matches():
    laps_df = pd.DataFrame([
        {"session_key": 9158, "driver_number": 1, "lap_number": 15},
    ])

    # Overlapping stint boundaries
    stints_df = pd.DataFrame([
        {"session_key": 9158, "driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 15},
        {"session_key": 9158, "driver_number": 1, "stint_number": 2, "lap_start": 15, "lap_end": 35},
    ])

    audit = DataValidator.validate_lap_to_stint_mapping(laps_df, stints_df)
    assert audit["valid"] is False
    assert audit["multi_mapped_laps"] == 1
