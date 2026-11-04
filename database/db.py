"""Database connection, engine factory, and schema initialization."""

import logging
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import settings

logger = logging.getLogger(__name__)


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Create and return a SQLAlchemy engine."""
    url = db_url or settings.DATABASE_URL
    # For SQLite, ensure directory exists and enable foreign keys
    if url.startswith("sqlite"):
        engine = create_engine(url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON;"))
        return engine
    return create_engine(url, echo=False)


def init_db(engine: Optional[Engine] = None, schema_path: Optional[Path] = None) -> None:
    """Initialize database tables from schema.sql."""
    eng = engine or get_engine()
    path = schema_path or (settings.DATABASE_DIR / "schema.sql")

    if not path.exists():
        raise FileNotFoundError(f"Schema file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Split statements for reliable execution
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

    with eng.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

    logger.info("Database schema initialized successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
