"""Harvester to fetch, cache, and record provenance for a given F1 session."""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from config import settings
from ingestion.api_client import OpenF1Client

logger = logging.getLogger(__name__)


class SessionDataFetcher:
    """Orchestrates ingestion of all datasets for an OpenF1 session."""

    def __init__(self, session_key: int, client: Optional[OpenF1Client] = None):
        self.session_key = session_key
        self.client = client or OpenF1Client()
        self.manifest_path = settings.RAW_DATA_DIR / f"{session_key}_manifest.json"

    def fetch_all(self, telemetry_driver_limit: int = settings.TELEMETRY_DRIVER_LIMIT) -> Dict[str, Any]:
        """Fetch all session datasets from OpenF1 and save raw snapshots with provenance."""
        retrieval_time = datetime.now(timezone.utc).isoformat()
        manifest: Dict[str, Any] = {
            "session_key": self.session_key,
            "retrieval_time_utc": retrieval_time,
            "endpoints": {},
            "status": "in_progress",
        }

        # 1. Session Metadata
        logger.info(f"Fetching session info for session_key={self.session_key}")
        sessions = self.client.get("sessions", params={"session_key": self.session_key})
        manifest["endpoints"]["sessions"] = {
            "count": len(sessions),
            "file": f"sessions_session_key-{self.session_key}.json",
        }

        meeting_key = sessions[0].get("meeting_key") if sessions else None

        # 2. Meetings Metadata
        meetings = []
        if meeting_key:
            logger.info(f"Fetching meetings info for meeting_key={meeting_key}")
            try:
                meetings = self.client.get("meetings", params={"meeting_key": meeting_key})
            except Exception as e:
                logger.warning(f"Could not fetch meetings endpoint: {e}")
        manifest["endpoints"]["meetings"] = {
            "count": len(meetings),
            "file": f"meetings_meeting_key-{meeting_key}.json" if meeting_key else None,
        }

        # 3. Drivers
        logger.info(f"Fetching drivers for session_key={self.session_key}")
        drivers = self.client.get("drivers", params={"session_key": self.session_key})
        manifest["endpoints"]["drivers"] = {
            "count": len(drivers),
            "file": f"drivers_session_key-{self.session_key}.json",
        }

        # 4. Laps
        logger.info(f"Fetching laps for session_key={self.session_key}")
        laps = self.client.get("laps", params={"session_key": self.session_key})
        manifest["endpoints"]["laps"] = {
            "count": len(laps),
            "file": f"laps_session_key-{self.session_key}.json",
        }

        # 5. Stints
        logger.info(f"Fetching stints for session_key={self.session_key}")
        stints = self.client.get("stints", params={"session_key": self.session_key})
        manifest["endpoints"]["stints"] = {
            "count": len(stints),
            "file": f"stints_session_key-{self.session_key}.json",
        }

        # 6. Pit stops
        logger.info(f"Fetching pit stops for session_key={self.session_key}")
        pit_stops = self.client.get("pit", params={"session_key": self.session_key})
        manifest["endpoints"]["pit"] = {
            "count": len(pit_stops),
            "file": f"pit_session_key-{self.session_key}.json",
        }

        # 7. Weather
        logger.info(f"Fetching weather for session_key={self.session_key}")
        weather = self.client.get("weather", params={"session_key": self.session_key})
        manifest["endpoints"]["weather"] = {
            "count": len(weather),
            "file": f"weather_session_key-{self.session_key}.json",
        }

        # 8. Race Control (Flags, SC, VSC)
        logger.info(f"Fetching race control events for session_key={self.session_key}")
        race_control = self.client.get("race_control", params={"session_key": self.session_key})
        manifest["endpoints"]["race_control"] = {
            "count": len(race_control),
            "file": f"race_control_session_key-{self.session_key}.json",
        }

        # 9. Car Data (Telemetry) - scoped to top N drivers to prevent network bloat
        telemetry_records = []
        driver_numbers = [d.get("driver_number") for d in drivers if d.get("driver_number") is not None]
        selected_drivers = driver_numbers[:telemetry_driver_limit] if telemetry_driver_limit > 0 else driver_numbers

        logger.info(f"Fetching telemetry for selected drivers: {selected_drivers}")
        for drv in selected_drivers:
            try:
                drv_telemetry = self.client.get(
                    "car_data",
                    params={"session_key": self.session_key, "driver_number": drv},
                )
                telemetry_records.extend(drv_telemetry)
            except Exception as e:
                logger.warning(f"Failed to fetch car_data for driver {drv}: {e}")

        manifest["endpoints"]["car_data"] = {
            "count": len(telemetry_records),
            "drivers_fetched": selected_drivers,
            "total_drivers_in_session": len(driver_numbers),
        }

        manifest["status"] = "completed"

        # Save manifest
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Harvest complete for session_key={self.session_key}. Manifest saved to {self.manifest_path}")
        return {
            "sessions": sessions,
            "meetings": meetings,
            "drivers": drivers,
            "laps": laps,
            "stints": stints,
            "pit": pit_stops,
            "weather": weather,
            "race_control": race_control,
            "car_data": telemetry_records,
            "manifest": manifest,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Harvest raw data for an F1 session from OpenF1.")
    parser.add_argument("--session_key", type=int, required=True, help="Session key to harvest")
    parser.add_argument(
        "--telemetry_drivers",
        type=int,
        default=settings.TELEMETRY_DRIVER_LIMIT,
        help="Number of drivers for which to fetch car telemetry",
    )
    args = parser.parse_args()

    fetcher = SessionDataFetcher(session_key=args.session_key)
    res = fetcher.fetch_all(telemetry_driver_limit=args.telemetry_drivers)
    print("\n--- Ingestion Manifest Summary ---")
    print(json.dumps(res["manifest"], indent=2))
