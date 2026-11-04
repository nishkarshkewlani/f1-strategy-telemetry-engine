"""Application configuration and path settings."""

import os
from pathlib import Path

# Load python-dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
DATABASE_DIR = BASE_DIR / "database"
SQL_QUERIES_DIR = BASE_DIR / "sql_queries"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

# Ensure runtime directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, SAMPLE_DATA_DIR, ARTIFACTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Configurations
OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1").rstrip("/")
JOLPICA_BASE_URL = os.getenv("JOLPICA_BASE_URL", "https://api.jolpi.ca/ergast/f1").rstrip("/")

REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "4"))
BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "1.5"))

# Database Configuration
DEFAULT_DB_PATH = BASE_DIR / "f1_engine.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")

# Telemetry Ingestion limits
TELEMETRY_DRIVER_LIMIT = int(os.getenv("TELEMETRY_DRIVER_LIMIT", "2"))

# App Environment
APP_ENV = os.getenv("APP_ENV", "development")
