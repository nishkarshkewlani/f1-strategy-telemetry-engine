"""Model Evaluation: Held-out validation, baseline comparisons, and residuals."""

import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import settings
from dashboard.components import apply_theme
from models.predict import LapTimePredictor

st.set_page_config(page_title="Model Evaluation - F1 Strategy Engine", page_icon="🏎️", layout="wide")

st.title("🤖 Predictive Model Validation & Performance")
st.caption("Rigorous Race-Grouped Holdout Validation (Held-out Race: 9157 Monza)")

# 1. Load Metrics Report
metrics_file = settings.ARTIFACTS_DIR / "lap_time_metrics.json"

if not metrics_file.exists():
    st.warning("No model evaluation metrics found. Please run model training first.")
    st.stop()

with open(metrics_file, "r", encoding="utf-8") as f:
    metrics = json.load(f)

# 2. Key Metrics Ribbon
k1, k2, k3, k4 = st.columns(4)
k1.metric("Training Samples", f"{metrics.get('train_samples', 0):,} laps")
k2.metric("Held-Out Test Samples", f"{metrics.get('test_samples', 0):,} laps")
gbm_metrics = metrics["models"].get("hist_gradient_boosting", {})
k3.metric("Candidate Model MAE", f"{gbm_metrics.get('mae', 0.0):.3f}s")
k4.metric("Candidate Model RMSE", f"{gbm_metrics.get('rmse', 0.0):.3f}s")

# 3. Model Comparison Table
st.markdown("### 🏆 Candidate Regressor vs. Baseline Comparison")
st.caption("Models evaluated strictly on held-out race (zero session overlap)")

model_rows = []
for model_name, m in metrics["models"].items():
    clean_name = model_name.replace("_", " ").title()
    model_rows.append({
        "Model Architecture": clean_name,
        "Held-Out MAE (s)": m.get("mae"),
        "Held-Out RMSE (s)": m.get("rmse"),
        "Held-Out R²": m.get("r2"),
    })

df_models = pd.DataFrame(model_rows).sort_values("Held-Out MAE (s)")
st.dataframe(df_models, hide_index=True, use_container_width=True)

# 4. Bar Chart Comparison
fig_models = px.bar(
    df_models,
    x="Model Architecture",
    y="Held-Out MAE (s)",
    color="Model Architecture",
    title="Model Prediction Error Comparison (Lower is Better)",
    labels={"Held-Out MAE (s)": "Mean Absolute Error (seconds)"},
)
st.plotly_chart(apply_theme(fig_models), use_container_width=True)

# 5. Interactive Lap Predictor Widget
st.markdown("### 🔮 Interactive Lap Time Predictor")
st.caption("Live inference using the fitted scikit-learn pipeline with empirical P10-P90 prediction intervals")

col_p1, col_p2, col_p3 = st.columns(3)
with col_p1:
    in_lap = st.number_input("Lap Number", min_value=1, max_value=60, value=20)
    in_age = st.number_input("Tyre Age (Laps)", min_value=0, max_value=40, value=15)
with col_p2:
    in_compound = st.selectbox("Compound", options=["HARD", "MEDIUM", "SOFT"], index=1)
    in_team = st.selectbox("Constructor", options=["Red Bull Racing", "Ferrari", "Mercedes", "McLaren"], index=0)
with col_p3:
    in_prev = st.number_input("Previous Lap Time (s)", min_value=70.0, max_value=120.0, value=86.2)
    in_track_temp = st.slider("Track Temp (°C)", min_value=20.0, max_value=55.0, value=38.0)

predictor = LapTimePredictor()
if st.button("Generate Lap Time Prediction", type="primary"):
    res = predictor.predict_lap(
        lap_number=in_lap,
        tyre_age=in_age,
        previous_lap_time=in_prev,
        compound=in_compound,
        team_name=in_team,
        track_temperature=in_track_temp,
    )

    pred_box = st.columns(3)
    pred_box[0].metric("Predicted Lap Time", f"{res['predicted_lap_time']:.3f}s")
    pred_box[1].metric("80% Lower Bound (P10)", f"{res['lower_interval_80pct']:.3f}s")
    pred_box[2].metric("80% Upper Bound (P90)", f"{res['upper_interval_80pct']:.3f}s")

    st.info(f"ℹ️ {res['confidence_disclaimer']}")
    if res["warnings"]:
        for w in res["warnings"]:
            st.warning(w)

# 6. Leakage Prevention & Audit Notes
st.markdown("### 🛡️ Leakage Prevention & Methodology")
st.markdown("""
- **Race-Grouped Cross-Validation:** Full sessions are kept completely out of training and testing to prevent neighbouring-lap correlation leakage.
- **Strictly Forward Features:** Only features available before the target lap begins are included. `previous_lap_time` is shifted by 1 within driver.
- **Target Lap Isolation:** No sector split from the target lap is present in the feature matrix.
- **Outlier Separation:** In-laps, pit-out laps, and safety-car neutralised laps are filtered out of training.
""")
