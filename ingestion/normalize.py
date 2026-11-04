"""Normalization and type casting for ingested F1 data payloads."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def parse_timestamp_utc(val: Any) -> Optional[str]:
    """Parse various timestamp formats into standard ISO-8601 UTC string."""
    if val is None or pd.isna(val) or val == "":
        return None
    try:
        dt = pd.to_datetime(val, utc=True)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception:
        return str(val)


def parse_timestamp_series(series: pd.Series) -> pd.Series:
    """Vectorized ISO-8601 UTC parsing for pandas Series."""
    if series.empty:
        return series
    try:
        dt = pd.to_datetime(series, utc=True, errors="coerce")
        return dt.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception:
        return series.astype(str)


def normalize_meetings(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize meetings data."""
    if not records:
        return pd.DataFrame(columns=["meeting_key", "year", "meeting_name", "country_name", "circuit_short_name", "location"])

    df = pd.DataFrame(records)
    cols = {
        "meeting_key": "meeting_key",
        "year": "year",
        "meeting_name": "meeting_name",
        "country_name": "country_name",
        "circuit_short_name": "circuit_short_name",
        "location": "location",
    }
    for col in cols:
        if col not in df.columns:
            df[col] = None

    df = df[list(cols.keys())].drop_duplicates(subset=["meeting_key"])
    df["meeting_key"] = pd.to_numeric(df["meeting_key"], errors="coerce").astype("Int64")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df.dropna(subset=["meeting_key"])


def normalize_sessions(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize sessions data."""
    if not records:
        return pd.DataFrame(columns=["session_key", "meeting_key", "session_name", "session_type", "date_start", "date_end"])

    df = pd.DataFrame(records)
    for col in ["session_key", "meeting_key", "session_name", "session_type", "date_start", "date_end"]:
        if col not in df.columns:
            df[col] = None

    df = df[["session_key", "meeting_key", "session_name", "session_type", "date_start", "date_end"]].drop_duplicates(subset=["session_key"])
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["meeting_key"] = pd.to_numeric(df["meeting_key"], errors="coerce").astype("Int64")
    df["date_start"] = parse_timestamp_series(df["date_start"])
    df["date_end"] = parse_timestamp_series(df["date_end"])
    return df.dropna(subset=["session_key"])


def normalize_drivers(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize drivers data."""
    if not records:
        return pd.DataFrame(columns=["session_key", "driver_number", "broadcast_name", "full_name", "name_acronym", "team_name", "team_colour"])

    df = pd.DataFrame(records)
    for col in ["session_key", "driver_number", "broadcast_name", "full_name", "name_acronym", "team_name", "team_colour"]:
        if col not in df.columns:
            df[col] = None

    df = df[["session_key", "driver_number", "broadcast_name", "full_name", "name_acronym", "team_name", "team_colour"]]
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["driver_number"] = pd.to_numeric(df["driver_number"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["session_key", "driver_number"]).drop_duplicates(subset=["session_key", "driver_number"])
    return df


def normalize_laps(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize laps data. Preserves null values for unrecorded sectors / lap times."""
    cols = [
        "session_key",
        "driver_number",
        "lap_number",
        "lap_duration",
        "duration_sector_1",
        "duration_sector_2",
        "duration_sector_3",
        "is_pit_out_lap",
        "date_start",
    ]
    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols].copy()
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["driver_number"] = pd.to_numeric(df["driver_number"], errors="coerce").astype("Int64")
    df["lap_number"] = pd.to_numeric(df["lap_number"], errors="coerce").astype("Int64")

    # Lap durations in seconds (float)
    for time_col in ["lap_duration", "duration_sector_1", "duration_sector_2", "duration_sector_3"]:
        df[time_col] = pd.to_numeric(df[time_col], errors="coerce")

    # Boolean is_pit_out_lap
    df["is_pit_out_lap"] = df["is_pit_out_lap"].fillna(False).astype(bool)
    df["date_start"] = parse_timestamp_series(df["date_start"])

    # Drop null primary keys and deduplicate
    df = df.dropna(subset=["session_key", "driver_number", "lap_number"]).drop_duplicates(
        subset=["session_key", "driver_number", "lap_number"]
    )
    return df


def normalize_stints(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize tyre stints data."""
    cols = ["session_key", "driver_number", "stint_number", "compound", "lap_start", "lap_end", "tyre_age_at_start"]
    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols].copy()
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["driver_number"] = pd.to_numeric(df["driver_number"], errors="coerce").astype("Int64")
    df["stint_number"] = pd.to_numeric(df["stint_number"], errors="coerce").astype("Int64")
    df["lap_start"] = pd.to_numeric(df["lap_start"], errors="coerce").astype("Int64")
    df["lap_end"] = pd.to_numeric(df["lap_end"], errors="coerce").astype("Int64")
    df["tyre_age_at_start"] = pd.to_numeric(df["tyre_age_at_start"], errors="coerce").fillna(0).astype("Int64")
    df["compound"] = df["compound"].astype(str).str.upper().replace({"NONE": None, "NAN": None})

    df = df.dropna(subset=["session_key", "driver_number", "stint_number"]).drop_duplicates(
        subset=["session_key", "driver_number", "stint_number"]
    )
    return df


def normalize_pit_stops(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize pit stops data."""
    cols = ["session_key", "driver_number", "lap_number", "pit_duration", "stop_duration", "date"]
    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols].copy()
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["driver_number"] = pd.to_numeric(df["driver_number"], errors="coerce").astype("Int64")
    df["lap_number"] = pd.to_numeric(df["lap_number"], errors="coerce").astype("Int64")
    df["pit_duration"] = pd.to_numeric(df["pit_duration"], errors="coerce")
    df["stop_duration"] = pd.to_numeric(df["stop_duration"], errors="coerce")
    df["date"] = parse_timestamp_series(df["date"])

    df = df.dropna(subset=["session_key", "driver_number", "lap_number"]).drop_duplicates(
        subset=["session_key", "driver_number", "lap_number"]
    )
    return df


def normalize_weather(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize weather observation data."""
    cols = [
        "session_key",
        "date",
        "air_temperature",
        "track_temperature",
        "humidity",
        "rainfall",
        "wind_speed",
        "wind_direction",
    ]
    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols].copy()
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["date"] = parse_timestamp_series(df["date"])
    for num_col in ["air_temperature", "track_temperature", "humidity", "rainfall", "wind_speed", "wind_direction"]:
        df[num_col] = pd.to_numeric(df[num_col], errors="coerce")

    df = df.dropna(subset=["session_key", "date"]).drop_duplicates(subset=["session_key", "date"])
    return df


def normalize_race_control(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize race control events."""
    cols = ["session_key", "date", "category", "flag", "message", "driver_number", "scope"]
    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols].copy()
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["driver_number"] = pd.to_numeric(df["driver_number"], errors="coerce").astype("Int64")
    df["date"] = parse_timestamp_series(df["date"])
    df["category"] = df["category"].astype(str)
    df["flag"] = df["flag"].astype(str).replace({"None": None, "nan": None})
    df["message"] = df["message"].astype(str)

    df = df.dropna(subset=["session_key", "date"]).drop_duplicates(subset=["session_key", "date", "message"])
    return df


def normalize_telemetry(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize high-frequency car telemetry (speed, throttle, brake, rpm, gear, drs)."""
    cols = ["session_key", "driver_number", "date", "speed", "throttle", "brake", "rpm", "n_gear", "drs"]
    if not records:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(records)
    for c in cols:
        if c not in df.columns:
            df[c] = None

    df = df[cols].copy()
    df["session_key"] = pd.to_numeric(df["session_key"], errors="coerce").astype("Int64")
    df["driver_number"] = pd.to_numeric(df["driver_number"], errors="coerce").astype("Int64")
    df["date"] = parse_timestamp_series(df["date"])

    # Sensor measurements: preserve nulls rather than converting to 0
    for num_col in ["speed", "throttle", "brake", "rpm", "n_gear", "drs"]:
        df[num_col] = pd.to_numeric(df[num_col], errors="coerce")

    df = df.dropna(subset=["session_key", "driver_number", "date"]).drop_duplicates(
        subset=["session_key", "driver_number", "date"]
    )
    return df
