"""Model B: Tyre degradation and compound association estimator."""

import json
import logging
from typing import Any, Dict
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import settings
from features.build_features import build_dataset

logger = logging.getLogger(__name__)


def train_tyre_model() -> Dict[str, Any]:
    """Train tyre degradation association model: lap_delta_from_fresh ~ compound + tyre_age."""
    df = build_dataset()
    if df.empty:
        raise ValueError("No data available.")

    clean = df[df["exclusion_reason"].isna() & df["tyre_age"].notna() & (df["tyre_age"] >= 0)].copy()

    # Calculate baseline fresh pace per driver and compound (median lap time at tyre_age <= 3)
    fresh_pace = (
        clean[clean["tyre_age"] <= 3]
        .groupby(["session_key", "driver_number", "compound"])["lap_duration"]
        .median()
        .reset_index()
        .rename(columns={"lap_duration": "fresh_pace"})
    )

    merged = pd.merge(clean, fresh_pace, on=["session_key", "driver_number", "compound"])
    merged["pace_delta_from_fresh"] = merged["lap_duration"] - merged["fresh_pace"]

    # Filter out extreme pace swings (traffic, yellow flags)
    valid = merged[merged["pace_delta_from_fresh"].between(-2.0, 5.0)].copy()

    X = valid[["tyre_age", "compound", "lap_number"]]
    y = valid["pace_delta_from_fresh"].values

    preprocessor = ColumnTransformer([
        ("num", StandardScaler(), ["tyre_age", "lap_number"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["compound"]),
    ])

    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", LinearRegression()),
    ])

    pipe.fit(X, y)

    # Save model artifact
    path = settings.ARTIFACTS_DIR / "tyre_degradation_model.joblib"
    joblib.dump(pipe, path)
    logger.info(f"Tyre degradation model saved to {path}")

    # Estimate average degradation slope per compound
    compound_slopes = {}
    for comp in valid["compound"].unique():
        sub = valid[valid["compound"] == comp]
        if len(sub) > 10:
            slope, _ = np.polyfit(sub["tyre_age"].values, sub["pace_delta_from_fresh"].values, 1)
            compound_slopes[str(comp)] = round(float(slope), 4)

    summary = {
        "samples_fitted": len(valid),
        "compound_slopes_sec_per_lap": compound_slopes,
    }
    with open(settings.ARTIFACTS_DIR / "tyre_metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = train_tyre_model()
    print("\n--- Tyre Degradation Association Report ---")
    print(json.dumps(res, indent=2))
