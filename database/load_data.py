"""Idempotent data loader to populate relational tables from raw/normalized data."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config import settings
from database.db import get_engine, init_db
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

logger = logging.getLogger(__name__)


class DatabaseLoader:
    """Loads normalized F1 session data into relational database with idempotent upsert."""

    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or get_engine()

    def upsert_dataframe(self, df: pd.DataFrame, table_name: str, primary_keys: List[str]) -> int:
        """Upsert a DataFrame into SQLite/PostgreSQL table idempotently."""
        if df.empty:
            return 0

        # Convert DataFrame NaNs to None for SQL NULLs
        clean_df = df.where(pd.notnull(df), None)
        records = clean_df.to_dict(orient="records")
        columns = list(clean_df.columns)

        col_names = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])

        # SQLite idempotent upsert: INSERT OR REPLACE
        sql_stmt = f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})"

        with self.engine.begin() as conn:
            conn.execute(text(sql_stmt), records)

        return len(records)

    def load_session_from_raw(self, session_key: int) -> Dict[str, int]:
        """Read cached raw JSON files for session_key, normalize, and upsert."""
        def load_json(filename: str) -> List[Dict[str, Any]]:
            path = settings.RAW_DATA_DIR / filename
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []

        raw_sessions = load_json(f"sessions_session_key-{session_key}.json")
        if not raw_sessions:
            raise FileNotFoundError(f"No session data found for session_key={session_key}")

        meeting_key = raw_sessions[0].get("meeting_key")
        raw_meetings = load_json(f"meetings_meeting_key-{meeting_key}.json") if meeting_key else []
        raw_drivers = load_json(f"drivers_session_key-{session_key}.json")
        raw_laps = load_json(f"laps_session_key-{session_key}.json")
        raw_stints = load_json(f"stints_session_key-{session_key}.json")
        raw_pit = load_json(f"pit_session_key-{session_key}.json")
        raw_weather = load_json(f"weather_session_key-{session_key}.json")
        raw_race_control = load_json(f"race_control_session_key-{session_key}.json")

        raw_telemetry = []
        for drv_file in settings.RAW_DATA_DIR.glob(f"car_data_driver_number-*_session_key-{session_key}.json"):
            with open(drv_file, "r", encoding="utf-8") as f:
                raw_telemetry.extend(json.load(f))

        # Normalize
        df_meetings = normalize_meetings(raw_meetings)
        df_sessions = normalize_sessions(raw_sessions)
        df_drivers = normalize_drivers(raw_drivers)
        df_laps = normalize_laps(raw_laps)
        df_stints = normalize_stints(raw_stints)
        df_pit = normalize_pit_stops(raw_pit)
        df_weather = normalize_weather(raw_weather)
        df_race_control = normalize_race_control(raw_race_control)
        df_telemetry = normalize_telemetry(raw_telemetry)

        # Upsert in relational order
        counts = {}
        counts["meetings"] = self.upsert_dataframe(df_meetings, "meetings", ["meeting_key"])
        counts["sessions"] = self.upsert_dataframe(df_sessions, "sessions", ["session_key"])
        counts["drivers"] = self.upsert_dataframe(df_drivers, "drivers", ["session_key", "driver_number"])
        counts["laps"] = self.upsert_dataframe(df_laps, "laps", ["session_key", "driver_number", "lap_number"])
        counts["tyre_stints"] = self.upsert_dataframe(df_stints, "tyre_stints", ["session_key", "driver_number", "stint_number"])
        counts["pit_stops"] = self.upsert_dataframe(df_pit, "pit_stops", ["session_key", "driver_number", "lap_number"])
        counts["weather"] = self.upsert_dataframe(df_weather, "weather", ["session_key", "date"])
        counts["race_events"] = self.upsert_dataframe(df_race_control, "race_events", ["session_key", "date", "message"])
        counts["telemetry"] = self.upsert_dataframe(df_telemetry, "telemetry", ["session_key", "driver_number", "date"])

        logger.info(f"Loaded session {session_key}: {counts}")
        return counts

    def get_table_counts(self) -> Dict[str, int]:
        """Return current row count for all database tables."""
        tables = ["meetings", "sessions", "drivers", "laps", "tyre_stints", "pit_stops", "weather", "race_events", "telemetry"]
        counts = {}
        with self.engine.connect() as conn:
            for tbl in tables:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                counts[tbl] = res.scalar() or 0
        return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load F1 session data into database.")
    parser.add_argument("--session_key", type=int, default=9157, help="Session key to load (default: 9157)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    init_db()
    loader = DatabaseLoader()
    print(f"\nInitial table counts: {loader.get_table_counts()}")
    
    print(f"\n--- First Ingestion Run for session {args.session_key} ---")
    counts_run1 = loader.load_session_from_raw(args.session_key)
    print(f"Upserted rows: {counts_run1}")
    print(f"Table counts after run 1: {loader.get_table_counts()}")

    print(f"\n--- Second Ingestion Run (Idempotency Test) for session {args.session_key} ---")
    counts_run2 = loader.load_session_from_raw(args.session_key)
    print(f"Upserted rows: {counts_run2}")
    counts_after_run2 = loader.get_table_counts()
    print(f"Table counts after run 2: {counts_after_run2}")
