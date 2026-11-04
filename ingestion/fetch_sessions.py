"""Discovery and selection of OpenF1 sessions."""

import argparse
import json
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from config import settings
from ingestion.api_client import OpenF1Client

logger = logging.getLogger(__name__)


def list_sessions(year: int = 2023, session_name: Optional[str] = "Race") -> pd.DataFrame:
    """Fetch and return available sessions for a specified year as a DataFrame.

    Args:
        year: Championship season year (e.g., 2023, 2024).
        session_name: Optional filter such as 'Race', 'Qualifying', 'Practice 1'.

    Returns:
        pd.DataFrame of discovered sessions.
    """
    client = OpenF1Client()
    params: Dict[str, Any] = {"year": year}
    if session_name:
        params["session_name"] = session_name

    records = client.get("sessions", params=params, use_cache=True)
    if not records:
        logger.warning(f"No sessions found for year={year}, session_name={session_name}")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    cols_to_show = [
        "session_key",
        "meeting_key",
        "year",
        "session_name",
        "session_type",
        "circuit_short_name",
        "country_name",
        "date_start",
    ]
    present_cols = [c for c in cols_to_show if c in df.columns]
    return df[present_cols]


def find_session_by_key(session_key: int) -> Optional[Dict[str, Any]]:
    """Look up session metadata by session_key."""
    client = OpenF1Client()
    records = client.get("sessions", params={"session_key": session_key}, use_cache=True)
    if records:
        return records[0]
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover available Formula 1 sessions from OpenF1.")
    parser.add_argument("--year", type=int, default=2023, help="Championship year (default: 2023)")
    parser.add_argument("--type", type=str, default="Race", help="Session type filter (default: Race)")
    args = parser.parse_args()

    sessions_df = list_sessions(year=args.year, session_name=args.type)
    if not sessions_df.empty:
        print(f"\n--- Discovered {len(sessions_df)} {args.type} Sessions for {args.year} ---")
        print(sessions_df.to_string(index=False))
    else:
        print("No matching sessions found.")
