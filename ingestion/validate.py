"""Data validation and data quality auditing for ingested F1 datasets."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates structural integrity, missingness, and motorsport business logic."""

    @staticmethod
    def audit_dataframe(df: pd.DataFrame, table_name: str, key_columns: List[str]) -> Dict[str, Any]:
        """Perform general audit on a table's missingness, keys, and row counts."""
        row_count = len(df)
        if row_count == 0:
            return {
                "table": table_name,
                "row_count": 0,
                "missingness": {},
                "duplicate_keys": 0,
                "status": "empty",
            }

        missingness = {col: round(float(df[col].isna().mean() * 100), 2) for col in df.columns}
        existing_keys = [k for k in key_columns if k in df.columns]
        duplicates = int(df.duplicated(subset=existing_keys).sum()) if existing_keys else 0

        return {
            "table": table_name,
            "row_count": row_count,
            "missingness_percent": missingness,
            "duplicate_keys": duplicates,
            "status": "passed" if duplicates == 0 else "warning_duplicates_found",
        }

    @staticmethod
    def validate_laps(laps_df: pd.DataFrame) -> Dict[str, Any]:
        """Validate lap data for motorsport plausibility."""
        if laps_df.empty:
            return {"status": "empty", "valid_laps": 0}

        # Check positive durations
        valid_lap_times = laps_df["lap_duration"].dropna()
        implausible_short = int((valid_lap_times < 45.0).sum())  # Faster than shortest F1 circuit lap
        implausible_long = int((valid_lap_times > 300.0).sum())   # Slower than 5 minutes (red flag or in-lap)

        return {
            "status": "passed" if implausible_short == 0 else "warning_implausible_lap_times",
            "total_laps": len(laps_df),
            "recorded_lap_times": len(valid_lap_times),
            "missing_lap_times": int(laps_df["lap_duration"].isna().sum()),
            "implausibly_short_laps": implausible_short,
            "extremely_long_laps": implausible_long,
            "min_lap_time": float(valid_lap_times.min()) if not valid_lap_times.empty else None,
            "max_lap_time": float(valid_lap_times.max()) if not valid_lap_times.empty else None,
        }

    @staticmethod
    def validate_lap_to_stint_mapping(laps_df: pd.DataFrame, stints_df: pd.DataFrame) -> Dict[str, Any]:
        """Verify that every lap maps to at most one tyre stint for the same driver & session."""
        if laps_df.empty or stints_df.empty:
            return {"status": "skipped_empty_data", "mapped_laps": 0, "multiple_matches": 0}

        unmapped = 0
        multi_mapped = 0
        total_checked = 0

        for (session_key, driver_number), driver_laps in laps_df.groupby(["session_key", "driver_number"]):
            driver_stints = stints_df[
                (stints_df["session_key"] == session_key) & (stints_df["driver_number"] == driver_number)
            ]
            for _, lap_row in driver_laps.iterrows():
                lap_num = lap_row["lap_number"]
                matching = driver_stints[
                    (driver_stints["lap_start"] <= lap_num) & (lap_num <= driver_stints["lap_end"])
                ]
                total_checked += 1
                if len(matching) == 0:
                    unmapped += 1
                elif len(matching) > 1:
                    multi_mapped += 1

        is_valid = multi_mapped == 0
        return {
            "status": "passed" if is_valid else "failed_multi_stint_mapping",
            "total_laps_checked": total_checked,
            "unmapped_laps": unmapped,
            "multi_mapped_laps": multi_mapped,
            "valid": is_valid,
        }

    @staticmethod
    def validate_telemetry(telemetry_df: pd.DataFrame) -> Dict[str, Any]:
        """Audit sensor telemetry values (speed, throttle, brake, RPM)."""
        if telemetry_df.empty:
            return {"status": "empty"}

        speed_valid = telemetry_df["speed"].dropna()
        throttle_valid = telemetry_df["throttle"].dropna()

        # Plausibility checks: Speed 0-400 km/h, Throttle 0-100%
        speed_anomalies = int(((speed_valid < 0) | (speed_valid > 400)).sum())
        throttle_anomalies = int(((throttle_valid < 0) | (throttle_valid > 105)).sum())

        return {
            "status": "passed" if speed_anomalies == 0 and throttle_anomalies == 0 else "warning_anomalies",
            "samples": len(telemetry_df),
            "speed_min": float(speed_valid.min()) if not speed_valid.empty else None,
            "speed_max": float(speed_valid.max()) if not speed_valid.empty else None,
            "speed_anomalies": speed_anomalies,
            "throttle_anomalies": throttle_anomalies,
        }
