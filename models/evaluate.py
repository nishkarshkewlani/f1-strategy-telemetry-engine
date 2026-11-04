"""Model evaluation reports, feature importance, and compound error breakdowns."""

import json
import logging
from typing import Any, Dict
import pandas as pd

from config import settings
from features.build_features import build_dataset, get_train_test_data
from models.predict import LapTimePredictor

logger = logging.getLogger(__name__)


def generate_evaluation_report(holdout_session_key: int = 9157) -> Dict[str, Any]:
    """Evaluate trained model on held-out race with compound and driver breakdowns."""
    predictor = LapTimePredictor()
    if predictor.model is None:
        raise RuntimeError("No trained model available.")

    df = build_dataset()
    _, test_df = get_train_test_data(df, holdout_session_key=holdout_session_key)

    if test_df.empty:
        return {"status": "no_test_data"}

    # Run inference
    features = ["lap_number", "tyre_age", "previous_lap_time", "track_temperature", "air_temperature", "compound", "team_name"]
    preds = predictor.model.predict(test_df[features])
    test_df["predicted_duration"] = preds
    test_df["error_seconds"] = test_df["predicted_duration"] - test_df["lap_duration"]
    test_df["abs_error"] = test_df["error_seconds"].abs()

    # Compound breakdown
    compound_breakdown = {}
    for comp, grp in test_df.groupby("compound"):
        compound_breakdown[comp] = {
            "laps": len(grp),
            "mae": round(float(grp["abs_error"].mean()), 3),
            "mean_error": round(float(grp["error_seconds"].mean()), 3),
        }

    # Driver breakdown
    driver_breakdown = {}
    for drv, grp in test_df.groupby("name_acronym"):
        driver_breakdown[drv] = {
            "laps": len(grp),
            "mae": round(float(grp["abs_error"].mean()), 3),
        }

    overall_mae = round(float(test_df["abs_error"].mean()), 3)
    overall_rmse = round(float((test_df["error_seconds"] ** 2).mean() ** 0.5), 3)

    report = {
        "holdout_session_key": holdout_session_key,
        "circuit": test_df["circuit"].iloc[0] if "circuit" in test_df.columns else "Unknown",
        "total_test_laps": len(test_df),
        "overall_mae": overall_mae,
        "overall_rmse": overall_rmse,
        "by_compound": compound_breakdown,
        "by_driver": driver_breakdown,
    }

    report_path = settings.ARTIFACTS_DIR / "heldout_evaluation_detailed.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rep = generate_evaluation_report(holdout_session_key=9157)
    print("\n--- Detailed Held-out Evaluation Report ---")
    print(json.dumps(rep, indent=2))
