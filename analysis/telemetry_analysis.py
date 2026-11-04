"""High-frequency telemetry trace comparison and sensor alignments."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from database.repository import F1Repository

logger = logging.getLogger(__name__)


class TelemetryAnalyzer:
    """Processes sensor data: speed, throttle, brake, RPM, gear, DRS."""

    def __init__(self, repository: Optional[F1Repository] = None):
        self.repo = repository or F1Repository()

    def get_driver_telemetry(self, session_key: int, driver_number: int) -> pd.DataFrame:
        """Fetch and clean telemetry for a driver in a session."""
        df = self.repo.get_telemetry(session_key=session_key, driver_number=driver_number)
        if df.empty:
            return pd.DataFrame()

        df["timestamp"] = pd.to_datetime(df["date"])
        # Relative time from session start
        t0 = df["timestamp"].min()
        df["relative_time_sec"] = (df["timestamp"] - t0).dt.total_seconds()
        return df

    def compare_drivers_speed_profile(
        self, session_key: int, driver_a: int, driver_b: int, sample_limit: int = 5000
    ) -> pd.DataFrame:
        """Fetch and align speed telemetry samples for two drivers."""
        tel_a = self.get_driver_telemetry(session_key, driver_a)
        tel_b = self.get_driver_telemetry(session_key, driver_b)

        if tel_a.empty or tel_b.empty:
            return pd.DataFrame()

        # Take matching time sample
        sample_a = tel_a.head(sample_limit)[["relative_time_sec", "speed", "throttle", "brake", "rpm", "n_gear", "drs"]].copy()
        sample_a["driver_number"] = driver_a

        sample_b = tel_b.head(sample_limit)[["relative_time_sec", "speed", "throttle", "brake", "rpm", "n_gear", "drs"]].copy()
        sample_b["driver_number"] = driver_b

        return pd.concat([sample_a, sample_b], ignore_index=True)
