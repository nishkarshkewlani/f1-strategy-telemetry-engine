"""Unit tests for ML model reloading, inference schema, and empirical intervals."""

from pathlib import Path
import pytest
from config import settings
from models.predict import LapTimePredictor


def test_model_artifact_exists():
    model_file = settings.ARTIFACTS_DIR / "lap_time_model.joblib"
    assert model_file.exists(), "Lap time model artifact was not saved."


def test_predictor_inference():
    predictor = LapTimePredictor()
    assert predictor.model is not None, "Model failed to load."

    pred = predictor.predict_lap(
        lap_number=15,
        tyre_age=10,
        previous_lap_time=86.5,
        compound="HARD",
        team_name="Red Bull Racing",
        track_temperature=38.0,
        air_temperature=28.0,
    )

    assert "predicted_lap_time" in pred
    assert 70.0 < pred["predicted_lap_time"] < 120.0
    assert pred["lower_interval_80pct"] < pred["predicted_lap_time"] < pred["upper_interval_80pct"]
    assert len(pred["warnings"]) == 0


def test_predictor_out_of_coverage_warning():
    predictor = LapTimePredictor()
    pred = predictor.predict_lap(
        lap_number=50,
        tyre_age=55,  # Exceeds realistic F1 tyre stint life
        previous_lap_time=88.0,
        compound="HYPERSOFT",  # Invalid / unusual compound
        team_name="Ferrari",
    )
    assert len(pred["warnings"]) >= 1
