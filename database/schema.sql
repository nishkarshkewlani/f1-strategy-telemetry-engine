-- Relational Database Schema for F1 Strategy & Telemetry Engine
-- Compatible with SQLite (default) and PostgreSQL

CREATE TABLE IF NOT EXISTS meetings (
    meeting_key INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    meeting_name TEXT NOT NULL,
    country_name TEXT,
    circuit_short_name TEXT,
    location TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_key INTEGER PRIMARY KEY,
    meeting_key INTEGER,
    session_name TEXT NOT NULL,
    session_type TEXT,
    date_start TEXT,
    date_end TEXT,
    FOREIGN KEY (meeting_key) REFERENCES meetings(meeting_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drivers (
    session_key INTEGER NOT NULL,
    driver_number INTEGER NOT NULL,
    broadcast_name TEXT,
    full_name TEXT,
    name_acronym TEXT,
    team_name TEXT,
    team_colour TEXT,
    PRIMARY KEY (session_key, driver_number),
    FOREIGN KEY (session_key) REFERENCES sessions(session_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS laps (
    session_key INTEGER NOT NULL,
    driver_number INTEGER NOT NULL,
    lap_number INTEGER NOT NULL,
    lap_duration REAL,
    duration_sector_1 REAL,
    duration_sector_2 REAL,
    duration_sector_3 REAL,
    is_pit_out_lap BOOLEAN DEFAULT 0,
    date_start TEXT,
    PRIMARY KEY (session_key, driver_number, lap_number),
    FOREIGN KEY (session_key, driver_number) REFERENCES drivers(session_key, driver_number) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tyre_stints (
    session_key INTEGER NOT NULL,
    driver_number INTEGER NOT NULL,
    stint_number INTEGER NOT NULL,
    compound TEXT,
    lap_start INTEGER NOT NULL,
    lap_end INTEGER NOT NULL,
    tyre_age_at_start INTEGER DEFAULT 0,
    PRIMARY KEY (session_key, driver_number, stint_number),
    FOREIGN KEY (session_key, driver_number) REFERENCES drivers(session_key, driver_number) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pit_stops (
    session_key INTEGER NOT NULL,
    driver_number INTEGER NOT NULL,
    lap_number INTEGER NOT NULL,
    pit_duration REAL,
    stop_duration REAL,
    date TEXT,
    PRIMARY KEY (session_key, driver_number, lap_number),
    FOREIGN KEY (session_key, driver_number) REFERENCES drivers(session_key, driver_number) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weather (
    weather_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key INTEGER NOT NULL,
    date TEXT NOT NULL,
    air_temperature REAL,
    track_temperature REAL,
    humidity REAL,
    rainfall REAL,
    wind_speed REAL,
    wind_direction REAL,
    UNIQUE(session_key, date),
    FOREIGN KEY (session_key) REFERENCES sessions(session_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS race_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key INTEGER NOT NULL,
    date TEXT NOT NULL,
    category TEXT,
    flag TEXT,
    message TEXT NOT NULL,
    driver_number INTEGER,
    scope TEXT,
    UNIQUE(session_key, date, message),
    FOREIGN KEY (session_key) REFERENCES sessions(session_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_key INTEGER NOT NULL,
    driver_number INTEGER NOT NULL,
    date TEXT NOT NULL,
    speed REAL,
    throttle REAL,
    brake REAL,
    rpm REAL,
    n_gear INTEGER,
    drs INTEGER,
    UNIQUE(session_key, driver_number, date),
    FOREIGN KEY (session_key, driver_number) REFERENCES drivers(session_key, driver_number) ON DELETE CASCADE
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_laps_session_driver ON laps(session_key, driver_number, lap_number);
CREATE INDEX IF NOT EXISTS idx_stints_lookup ON tyre_stints(session_key, driver_number, lap_start, lap_end);
CREATE INDEX IF NOT EXISTS idx_telemetry_driver_ts ON telemetry(session_key, driver_number, date);
CREATE INDEX IF NOT EXISTS idx_weather_session_date ON weather(session_key, date);
