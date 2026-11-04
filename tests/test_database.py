"""Unit tests for relational database schema, upsert idempotency, and repository queries."""

import pytest
from sqlalchemy import create_engine, text

from database.db import init_db
from database.load_data import DatabaseLoader
from database.repository import F1Repository
import pandas as pd


@pytest.fixture
def test_db(tmp_path):
    """Creates a fresh SQLite database for testing."""
    db_file = tmp_path / "test_f1.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
    init_db(engine=engine)
    return engine


def test_schema_creation(test_db):
    """Verify all expected tables and indexes exist."""
    with test_db.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = [row[0] for row in result.fetchall()]

    expected = ["meetings", "sessions", "drivers", "laps", "tyre_stints", "pit_stops", "weather", "race_events", "telemetry"]
    for tbl in expected:
        assert tbl in tables


def test_idempotent_upsert(test_db):
    """Verify that inserting duplicate records does not inflate table row counts."""
    loader = DatabaseLoader(engine=test_db)

    # Insert prerequisite meeting and session for FK integrity
    loader.upsert_dataframe(
        pd.DataFrame([{"meeting_key": 100, "year": 2023, "meeting_name": "Bahrain GP"}]),
        "meetings",
        ["meeting_key"],
    )
    loader.upsert_dataframe(
        pd.DataFrame([{"session_key": 9158, "meeting_key": 100, "session_name": "Race"}]),
        "sessions",
        ["session_key"],
    )

    # Sample driver records
    drivers_df = pd.DataFrame([
        {
            "session_key": 9158,
            "driver_number": 1,
            "broadcast_name": "M VERSTAPPEN",
            "full_name": "Max Verstappen",
            "name_acronym": "VER",
            "team_name": "Red Bull Racing",
            "team_colour": "3671C6",
        },
        {
            "session_key": 9158,
            "driver_number": 11,
            "broadcast_name": "S PEREZ",
            "full_name": "Sergio Perez",
            "name_acronym": "PER",
            "team_name": "Red Bull Racing",
            "team_colour": "3671C6",
        },
    ])

    # First run
    inserted_1 = loader.upsert_dataframe(drivers_df, "drivers", ["session_key", "driver_number"])
    assert inserted_1 == 2
    counts_1 = loader.get_table_counts()
    assert counts_1["drivers"] == 2

    # Second run with exact same data
    inserted_2 = loader.upsert_dataframe(drivers_df, "drivers", ["session_key", "driver_number"])
    assert inserted_2 == 2
    counts_2 = loader.get_table_counts()
    # Count must remain exactly 2, proving idempotency
    assert counts_2["drivers"] == 2


def test_repository_laps_query(test_db):
    """Verify F1Repository parameterized lap retrieval."""
    loader = DatabaseLoader(engine=test_db)

    # Insert prerequisite meeting, session, driver
    loader.upsert_dataframe(
        pd.DataFrame([{"meeting_key": 100, "year": 2023, "meeting_name": "Bahrain GP"}]),
        "meetings",
        ["meeting_key"],
    )
    loader.upsert_dataframe(
        pd.DataFrame([{"session_key": 9158, "meeting_key": 100, "session_name": "Race"}]),
        "sessions",
        ["session_key"],
    )
    loader.upsert_dataframe(
        pd.DataFrame([{"session_key": 9158, "driver_number": 1, "name_acronym": "VER", "team_name": "Red Bull"}]),
        "drivers",
        ["session_key", "driver_number"],
    )

    # Insert laps
    laps_df = pd.DataFrame([
        {"session_key": 9158, "driver_number": 1, "lap_number": 1, "lap_duration": 96.5, "is_pit_out_lap": False},
        {"session_key": 9158, "driver_number": 1, "lap_number": 2, "lap_duration": 94.2, "is_pit_out_lap": False},
    ])
    loader.upsert_dataframe(laps_df, "laps", ["session_key", "driver_number", "lap_number"])

    repo = F1Repository(engine=test_db)
    fetched_laps = repo.get_laps(session_key=9158, driver_number=1)
    assert len(fetched_laps) == 2
    assert fetched_laps.iloc[0]["lap_duration"] == 96.5
    assert fetched_laps.iloc[1]["lap_duration"] == 94.2
