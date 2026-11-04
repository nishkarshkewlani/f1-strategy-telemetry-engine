"""Lap time analysis, consistency statistics, and pace distributions."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from database.repository import F1Repository

logger = logging.getLogger(__name__)


class LapAnalyzer:
    """Computes race pace metrics, sector analysis, and consistency indices."""

    def __init__(self, repository: Optional[F1Repository] = None):
        self.repo = repository or F1Repository()

    def get_clean_race_laps(self, session_key: int, driver_number: Optional[int] = None) -> pd.DataFrame:
        """Fetch laps excluding pit out laps and extreme outlier laps (e.g. SC / incident)."""
        laps_df = self.repo.get_laps(session_key=session_key, driver_number=driver_number)
        if laps_df.empty:
            return pd.DataFrame()

        # Exclude pit-out laps and non-timed laps
        clean = laps_df[
            (~laps_df["is_pit_out_lap"]) & (laps_df["lap_duration"].notna()) & (laps_df["lap_duration"] > 0)
        ].copy()

        # Exclude laps > 1.15 * driver median lap time (safety cars, slow in-laps)
        driver_medians = clean.groupby("driver_number")["lap_duration"].transform("median")
        clean = clean[clean["lap_duration"] <= driver_medians * 1.15].copy()
        return clean

    def calculate_driver_consistency(self, session_key: int) -> pd.DataFrame:
        """Calculate pace consistency metrics: Mean, Median, StdDev, IQR."""
        clean_laps = self.get_clean_race_laps(session_key)
        if clean_laps.empty:
            return pd.DataFrame()

        def compute_iqr(series: pd.Series) -> float:
            return float(series.quantile(0.75) - series.quantile(0.25))

        stats = (
            clean_laps.groupby(["driver_number", "name_acronym", "team_name"])["lap_duration"]
            .agg(
                clean_laps_count="count",
                median_pace="median",
                mean_pace="mean",
                std_pace="std",
                fastest_lap="min",
                iqr_pace=compute_iqr,
            )
            .reset_index()
        )

        stats["median_pace"] = stats["median_pace"].round(3)
        stats["mean_pace"] = stats["mean_pace"].round(3)
        stats["std_pace"] = stats["std_pace"].round(3)
        stats["fastest_lap"] = stats["fastest_lap"].round(3)
        stats["iqr_pace"] = stats["iqr_pace"].round(3)

        return stats.sort_values(by="median_pace", ascending=True)

    def get_lap_delta_evolution(self, session_key: int, driver_numbers: List[int]) -> pd.DataFrame:
        """Fetch lap time evolution for selected drivers side by side."""
        laps = self.repo.get_laps(session_key)
        if laps.empty:
            return pd.DataFrame()

        filtered = laps[laps["driver_number"].isin(driver_numbers) & laps["lap_duration"].notna()].copy()
        return filtered[["driver_number", "name_acronym", "lap_number", "lap_duration", "is_pit_out_lap"]]
