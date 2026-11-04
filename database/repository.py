"""Repository layer for parameterized SQL queries and database access."""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from database.db import get_engine

logger = logging.getLogger(__name__)


class F1Repository:
    """Provides type-safe, parameterized access to the relational database."""

    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or get_engine()

    def get_all_sessions(self) -> pd.DataFrame:
        """Fetch all ingested sessions with meeting details."""
        query = text("""
            SELECT 
                s.session_key,
                s.session_name,
                s.session_type,
                s.date_start,
                m.meeting_key,
                m.meeting_name,
                m.country_name,
                m.circuit_short_name,
                m.year
            FROM sessions s
            LEFT JOIN meetings m ON s.meeting_key = m.meeting_key
            ORDER BY s.date_start DESC
        """)
        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn)

    def get_drivers_by_session(self, session_key: int) -> pd.DataFrame:
        """Fetch all drivers participating in a session."""
        query = text("""
            SELECT 
                session_key,
                driver_number,
                broadcast_name,
                full_name,
                name_acronym,
                team_name,
                team_colour
            FROM drivers
            WHERE session_key = :session_key
            ORDER BY team_name, driver_number
        """)
        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn, params={"session_key": session_key})

    def get_laps(self, session_key: int, driver_number: Optional[int] = None) -> pd.DataFrame:
        """Fetch laps for a session, optionally filtered by driver."""
        if driver_number is not None:
            query = text("""
                SELECT 
                    l.session_key,
                    l.driver_number,
                    d.name_acronym,
                    d.team_name,
                    l.lap_number,
                    l.lap_duration,
                    l.duration_sector_1,
                    l.duration_sector_2,
                    l.duration_sector_3,
                    l.is_pit_out_lap,
                    l.date_start
                FROM laps l
                JOIN drivers d ON l.session_key = d.session_key AND l.driver_number = d.driver_number
                WHERE l.session_key = :session_key AND l.driver_number = :driver_number
                ORDER BY l.lap_number ASC
            """)
            params = {"session_key": session_key, "driver_number": driver_number}
        else:
            query = text("""
                SELECT 
                    l.session_key,
                    l.driver_number,
                    d.name_acronym,
                    d.team_name,
                    l.lap_number,
                    l.lap_duration,
                    l.duration_sector_1,
                    l.duration_sector_2,
                    l.duration_sector_3,
                    l.is_pit_out_lap,
                    l.date_start
                FROM laps l
                JOIN drivers d ON l.session_key = d.session_key AND l.driver_number = d.driver_number
                WHERE l.session_key = :session_key
                ORDER BY l.driver_number, l.lap_number ASC
            """)
            params = {"session_key": session_key}

        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def get_stints(self, session_key: int, driver_number: Optional[int] = None) -> pd.DataFrame:
        """Fetch tyre stints for a session."""
        if driver_number is not None:
            query = text("""
                SELECT 
                    s.session_key,
                    s.driver_number,
                    d.name_acronym,
                    s.stint_number,
                    s.compound,
                    s.lap_start,
                    s.lap_end,
                    s.tyre_age_at_start
                FROM tyre_stints s
                JOIN drivers d ON s.session_key = d.session_key AND s.driver_number = d.driver_number
                WHERE s.session_key = :session_key AND s.driver_number = :driver_number
                ORDER BY s.stint_number ASC
            """)
            params = {"session_key": session_key, "driver_number": driver_number}
        else:
            query = text("""
                SELECT 
                    s.session_key,
                    s.driver_number,
                    d.name_acronym,
                    s.stint_number,
                    s.compound,
                    s.lap_start,
                    s.lap_end,
                    s.tyre_age_at_start
                FROM tyre_stints s
                JOIN drivers d ON s.session_key = d.session_key AND s.driver_number = d.driver_number
                WHERE s.session_key = :session_key
                ORDER BY s.driver_number, s.stint_number ASC
            """)
            params = {"session_key": session_key}

        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def get_pit_stops(self, session_key: int) -> pd.DataFrame:
        """Fetch pit stop records for a session."""
        query = text("""
            SELECT 
                p.session_key,
                p.driver_number,
                d.name_acronym,
                d.team_name,
                p.lap_number,
                p.pit_duration,
                p.stop_duration,
                p.date
            FROM pit_stops p
            JOIN drivers d ON p.session_key = d.session_key AND p.driver_number = d.driver_number
            WHERE p.session_key = :session_key
            ORDER BY p.lap_number ASC
        """)
        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn, params={"session_key": session_key})

    def get_telemetry(self, session_key: int, driver_number: int) -> pd.DataFrame:
        """Fetch high-frequency car telemetry samples for a driver in a session."""
        query = text("""
            SELECT 
                session_key,
                driver_number,
                date,
                speed,
                throttle,
                brake,
                rpm,
                n_gear,
                drs
            FROM telemetry
            WHERE session_key = :session_key AND driver_number = :driver_number
            ORDER BY date ASC
        """)
        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn, params={"session_key": session_key, "driver_number": driver_number})

    def get_weather(self, session_key: int) -> pd.DataFrame:
        """Fetch weather observations for a session."""
        query = text("""
            SELECT 
                session_key,
                date,
                air_temperature,
                track_temperature,
                humidity,
                rainfall,
                wind_speed,
                wind_direction
            FROM weather
            WHERE session_key = :session_key
            ORDER BY date ASC
        """)
        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn, params={"session_key": session_key})

    def get_race_events(self, session_key: int) -> pd.DataFrame:
        """Fetch race control flag and safety-car events."""
        query = text("""
            SELECT 
                session_key,
                date,
                category,
                flag,
                message,
                driver_number,
                scope
            FROM race_events
            WHERE session_key = :session_key
            ORDER BY date ASC
        """)
        with self.engine.connect() as conn:
            return pd.read_sql_query(query, conn, params={"session_key": session_key})

    def execute_custom_sql(self, sql_query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute arbitrary parameterized SQL query and return DataFrame."""
        with self.engine.connect() as conn:
            return pd.read_sql_query(text(sql_query), conn, params=params or {})
