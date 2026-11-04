"""Data quality audit script for harvested F1 sessions."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict
import pandas as pd

from config import settings
from ingestion.normalize import (
    normalize_drivers,
    normalize_laps,
    normalize_meetings,
    normalize_pit_stops,
    normalize_race_control,
    normalize_sessions,
    normalize_stints,
    normalize_telemetry,
    normalize_weather,
)
from ingestion.validate import DataValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def audit_session(session_key: int) -> Dict[str, Any]:
    """Run full structural and domain audits on a stored session."""
    manifest_file = settings.RAW_DATA_DIR / f"{session_key}_manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest for session {session_key} not found at {manifest_file}")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Helper to load raw JSON
    def load_json(name: str):
        p = settings.RAW_DATA_DIR / name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    # Load and normalize
    raw_sessions = load_json(f"sessions_session_key-{session_key}.json")
    meeting_key = raw_sessions[0].get("meeting_key") if raw_sessions else None
    raw_meetings = load_json(f"meetings_meeting_key-{meeting_key}.json") if meeting_key else []
    raw_drivers = load_json(f"drivers_session_key-{session_key}.json")
    raw_laps = load_json(f"laps_session_key-{session_key}.json")
    raw_stints = load_json(f"stints_session_key-{session_key}.json")
    raw_pit = load_json(f"pit_session_key-{session_key}.json")
    raw_weather = load_json(f"weather_session_key-{session_key}.json")
    raw_race_control = load_json(f"race_control_session_key-{session_key}.json")

    # Load telemetry for drivers
    raw_telemetry = []
    for drv_file in settings.RAW_DATA_DIR.glob(f"car_data_driver_number-*_session_key-{session_key}.json"):
        with open(drv_file, "r", encoding="utf-8") as f:
            raw_telemetry.extend(json.load(f))

    df_sessions = normalize_sessions(raw_sessions)
    df_meetings = normalize_meetings(raw_meetings)
    df_drivers = normalize_drivers(raw_drivers)
    df_laps = normalize_laps(raw_laps)
    df_stints = normalize_stints(raw_stints)
    df_pit = normalize_pit_stops(raw_pit)
    df_weather = normalize_weather(raw_weather)
    df_race_control = normalize_race_control(raw_race_control)
    df_telemetry = normalize_telemetry(raw_telemetry)

    report = {
        "session_key": session_key,
        "circuit": raw_sessions[0].get("circuit_short_name") if raw_sessions else "Unknown",
        "tables": {
            "sessions": DataValidator.audit_dataframe(df_sessions, "sessions", ["session_key"]),
            "meetings": DataValidator.audit_dataframe(df_meetings, "meetings", ["meeting_key"]),
            "drivers": DataValidator.audit_dataframe(df_drivers, "drivers", ["session_key", "driver_number"]),
            "laps": DataValidator.audit_dataframe(df_laps, "laps", ["session_key", "driver_number", "lap_number"]),
            "stints": DataValidator.audit_dataframe(df_stints, "stints", ["session_key", "driver_number", "stint_number"]),
            "pit_stops": DataValidator.audit_dataframe(df_pit, "pit_stops", ["session_key", "driver_number", "lap_number"]),
            "weather": DataValidator.audit_dataframe(df_weather, "weather", ["session_key", "date"]),
            "race_control": DataValidator.audit_dataframe(df_race_control, "race_control", ["session_key", "date", "message"]),
            "telemetry": DataValidator.audit_dataframe(df_telemetry, "telemetry", ["session_key", "driver_number", "date"]),
        },
        "domain_checks": {
            "laps_plausibility": DataValidator.validate_laps(df_laps),
            "lap_to_stint_mapping": DataValidator.validate_lap_to_stint_mapping(df_laps, df_stints),
            "telemetry_plausibility": DataValidator.validate_telemetry(df_telemetry),
        },
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit data quality for harvested sessions.")
    parser.add_argument("--session_key", type=int, default=9157, help="Session key to audit (default: 9157)")
    args = parser.parse_args()

    audit_result = audit_session(args.session_key)
    print("\n================ DATA QUALITY AUDIT REPORT ================")
    print(f"Session Key: {audit_result['session_key']} ({audit_result['circuit']})")
    print("\n--- Table Summaries ---")
    for tbl, res in audit_result["tables"].items():
        print(f"  [{tbl}] Rows: {res['row_count']}, Duplicate Keys: {res['duplicate_keys']}, Status: {res['status']}")

    print("\n--- Domain Logic Checks ---")
    for chk, res in audit_result["domain_checks"].items():
        print(f"  [{chk}]: {res['status']}")
        for k, v in res.items():
            if k != "status":
                print(f"      {k}: {v}")
    print("===========================================================")
