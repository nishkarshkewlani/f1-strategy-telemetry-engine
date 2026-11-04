"""Model training for lap-time regression with session-grouped holdout validation."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import settings
from features.build_features import build_dataset, get_train_test_data

logger = logging.getLogger(__name__)


NUMERIC_FEATURES = ["lap_number", "tyre_age", "previous_lap_time", "track_temperature", "air_temperature"]
CATEGORICAL_FEATURES = ["compound", "team_name"]
TARGET = "lap_duration"


def create_preprocessor() -> ColumnTransformer:
    """Build scikit-learn preprocessing ColumnTransformer."""
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    return ColumnTransformer([
        ("num", numeric_transformer, NUMERIC_FEATURES),
        ("cat", categorical_transformer, CATEGORICAL_FEATURES),
    ])


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate MAE, RMSE, and R2."""
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    return {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)}


def train_and_evaluate(holdout_session_key: int = 9157) -> Dict[str, Any]:
    """Train baseline vs candidate regressors with race-grouped validation."""
    logger.info("Building feature dataset from database...")
    df = build_dataset()
    if df.empty:
        raise ValueError("Dataset is empty. Ensure sessions are loaded into database.")

    train_df, test_df = get_train_test_data(df, holdout_session_key=holdout_session_key)
    logger.info(f"Dataset split: Train={len(train_df)} laps, Held-out Test={len(test_df)} laps (session {holdout_session_key})")

    X_train = train_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_train = train_df[TARGET].values

    X_test = test_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_test = test_df[TARGET].values

    # 1. Baseline Model: Median Predictor
    baseline_dummy = DummyRegressor(strategy="median")
    baseline_dummy.fit(X_train, y_train)
    y_pred_baseline = baseline_dummy.predict(X_test)
    baseline_metrics = evaluate_predictions(y_test, y_pred_baseline)

    # 2. Linear Baseline: Ridge Regression
    linear_pipe = Pipeline([
        ("preprocessor", create_preprocessor()),
        ("regressor", Ridge(alpha=1.0)),
    ])
    linear_pipe.fit(X_train, y_train)
    y_pred_linear = linear_pipe.predict(X_test)
    linear_metrics = evaluate_predictions(y_test, y_pred_linear)

    # 3. Candidate Regressor: HistGradientBoostingRegressor
    gbm_pipe = Pipeline([
        ("preprocessor", create_preprocessor()),
        ("regressor", HistGradientBoostingRegressor(max_iter=100, random_state=42)),
    ])
    gbm_pipe.fit(X_train, y_train)
    y_pred_gbm = gbm_pipe.predict(X_test)
    gbm_metrics = evaluate_predictions(y_test, y_pred_gbm)

    # 4. Candidate Regressor: RandomForestRegressor
    rf_pipe = Pipeline([
        ("preprocessor", create_preprocessor()),
        ("regressor", RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)),
    ])
    rf_pipe.fit(X_train, y_train)
    y_pred_rf = rf_pipe.predict(X_test)
    rf_metrics = evaluate_predictions(y_test, y_pred_rf)

    # Calculate centered empirical prediction residuals (for uncertainty intervals)
    residuals = y_test - y_pred_gbm
    res_centered = residuals - np.mean(residuals)
    q10 = float(np.percentile(res_centered, 10))
    q90 = float(np.percentile(res_centered, 90))

    report = {
        "holdout_session_key": holdout_session_key,
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "models": {
            "dummy_median_baseline": baseline_metrics,
            "ridge_linear_regression": linear_metrics,
            "hist_gradient_boosting": gbm_metrics,
            "random_forest": rf_metrics,
        },
        "empirical_residuals": {
            "residual_mean": round(float(np.mean(residuals)), 4),
            "residual_q10": round(q10, 4),
            "residual_q90": round(q90, 4),
        },
    }

    # Select best model: HistGradientBoostingRegressor
    # Fit final pipeline on all available clean data for production deployment
    clean_all = df[df["exclusion_reason"].isna()].copy()
    X_all = clean_all[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y_all = clean_all[TARGET].values

    final_model = Pipeline([
        ("preprocessor", create_preprocessor()),
        ("regressor", HistGradientBoostingRegressor(max_iter=150, random_state=42)),
    ])
    final_model.fit(X_all, y_all)

    # Save model and metadata artifact
    artifact_path = settings.ARTIFACTS_DIR / "lap_time_model.joblib"
    joblib.dump(final_model, artifact_path)

    metrics_path = settings.ARTIFACTS_DIR / "lap_time_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Model saved to {artifact_path}. Metrics saved to {metrics_path}")
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = train_and_evaluate(holdout_session_key=9157)
    print("\n--- Model Evaluation Report (Held-out Race: 9157 Monza) ---")
    print(json.dumps(res, indent=2))
