"""Tyre degradation curve analysis, compound life trends, and stint evaluations."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from database.repository import F1Repository

logger = logging.getLogger(__name__)


class TyreAnalyzer:
    """Analyzes tyre wear trends and pace degradation slopes by compound."""

    def __init__(self, repository: Optional[F1Repository] = None):
        self.repo = repository or F1Repository()

    def get_stints_with_pace(self, session_key: int) -> pd.DataFrame:
        """Join laps to tyre stints and compute lap-level tyre age."""
        laps = self.repo.get_laps(session_key)
        stints = self.repo.get_stints(session_key)

        if laps.empty or stints.empty:
            return pd.DataFrame()

        records = []
        for (drv, stint_num), stint_row in stints.groupby(["driver_number", "stint_number"]):
            s_row = stint_row.iloc[0]
            compound = s_row["compound"]
            lap_start = s_row["lap_start"]
            lap_end = s_row["lap_end"]
            age_start = s_row["tyre_age_at_start"]

            driver_laps = laps[(laps["driver_number"] == drv) & (laps["lap_number"].between(lap_start, lap_end))].copy()
            if driver_laps.empty:
                continue

            # Compute tyre age: age_start + (lap_number - lap_start)
            driver_laps["stint_number"] = stint_num
            driver_laps["compound"] = compound
            driver_laps["tyre_age"] = age_start + (driver_laps["lap_number"] - lap_start)
            records.append(driver_laps)

        if not records:
            return pd.DataFrame()

        df_merged = pd.concat(records, ignore_index=True)
        return df_merged

    def estimate_compound_degradation(self, session_key: int) -> pd.DataFrame:
        """Estimate linear degradation slope (seconds lost per lap of tyre age) per compound."""
        df = self.get_stints_with_pace(session_key)
        if df.empty:
            return pd.DataFrame()

        # Clean laps: exclude pit-out laps and outliers
        clean = df[(~df["is_pit_out_lap"]) & (df["lap_duration"].notna()) & (df["lap_duration"] > 0)].copy()

        # Filter out safety-car affected laps
        clean = clean[clean["lap_duration"] < clean["lap_duration"].quantile(0.90)]

        results = []
        for compound, group in clean.groupby("compound"):
            if len(group) < 10 or group["tyre_age"].nunique() < 3:
                continue

            # Simple linear regression: lap_duration ~ slope * tyre_age + intercept
            x = group["tyre_age"].values
            y = group["lap_duration"].values

            slope, intercept = np.polyfit(x, y, 1)
            results.append({
                "compound": compound,
                "laps_observed": len(group),
                "drivers_represented": group["driver_number"].nunique(),
                "base_pace_seconds": round(float(intercept), 3),
                "degradation_sec_per_lap": round(float(slope), 4),
                "max_tyre_age_observed": int(group["tyre_age"].max()),
            })

        return pd.DataFrame(results).sort_values(by="base_pace_seconds")
