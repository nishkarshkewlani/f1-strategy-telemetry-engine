"""Inference service for lap-time predictions with empirical uncertainty intervals."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd

from config import settings

logger = logging.getLogger(__name__)


class LapTimePredictor:
    """Loads trained pipeline and serves lap-time predictions with uncertainty bounds."""

    def __init__(self, model_path: Optional[Path] = None, metrics_path: Optional[Path] = None):
        self.model_path = model_path or (settings.ARTIFACTS_DIR / "lap_time_model.joblib")
        self.metrics_path = metrics_path or (settings.ARTIFACTS_DIR / "lap_time_metrics.json")
        self.model = None
        self.residuals = {"q10": -0.85, "q90": 0.85}
        self._load()

    def _load(self):
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
            logger.info(f"Loaded lap-time model from {self.model_path}")
        else:
            logger.warning(f"No trained model artifact found at {self.model_path}")

        if self.metrics_path.exists():
            with open(self.metrics_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                emp = data.get("empirical_residuals", {})
                self.residuals["q10"] = emp.get("residual_q10", -0.85)
                self.residuals["q90"] = emp.get("residual_q90", 0.85)

    def predict_lap(
        self,
        lap_number: int,
        tyre_age: int,
        previous_lap_time: float,
        compound: str,
        team_name: str,
        track_temperature: float = 35.0,
        air_temperature: float = 25.0,
    ) -> Dict[str, Any]:
        """Predict lap time in seconds with empirical uncertainty intervals."""
        if self.model is None:
            raise RuntimeError("Model is not loaded. Train the model first.")

        df_input = pd.DataFrame([{
            "lap_number": lap_number,
            "tyre_age": tyre_age,
            "previous_lap_time": previous_lap_time,
            "track_temperature": track_temperature,
            "air_temperature": air_temperature,
            "compound": str(compound).upper(),
            "team_name": str(team_name),
        }])

        warnings = []
        if tyre_age > 45:
            warnings.append(f"Tyre age ({tyre_age} laps) exceeds standard stint limits.")
        if compound.upper() not in ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]:
            warnings.append(f"Unusual tyre compound '{compound}'.")

        pred_val = float(self.model.predict(df_input)[0])

        return {
            "predicted_lap_time": round(pred_val, 3),
            "lower_interval_80pct": round(pred_val + self.residuals["q10"], 3),
            "upper_interval_80pct": round(pred_val + self.residuals["q90"], 3),
            "confidence_disclaimer": "Empirical interval based on held-out race residual quantiles (P10-P90).",
            "warnings": warnings,
        }
