"""Pit Stop Strategy Simulator and Decision Engine."""

from pathlib import Path
import sys
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dashboard.components import plot_strategy_comparison
from database.repository import F1Repository
from strategy.cost_model import StrategyCostModel
from strategy.pit_optimizer import PitOptimizer

st.set_page_config(page_title="Pit Strategy - F1 Strategy Engine", page_icon="🏎️", layout="wide")

repo = F1Repository()

session_key = st.session_state.get("selected_session_key")
if not session_key:
    sessions = repo.get_all_sessions()
    if not sessions.empty:
        session_key = int(sessions.iloc[0]["session_key"])
    else:
        st.error("No sessions available.")
        st.stop()

st.title("🎯 Pit Stop Strategy Simulator")
st.caption(f"Session Key: `{session_key}` | Prescriptive Candidate Evaluation & Pit Window Optimizer")

# --- Race State Inputs Form ---
st.markdown("### 🛠️ Configure Current Race State")

drivers_df = repo.get_drivers_by_session(session_key)
driver_options = {
    int(row["driver_number"]): f"#{row['driver_number']} {row['name_acronym']} ({row['team_name']})"
    for _, row in drivers_df.iterrows()
} if not drivers_df.empty else {1: "#1 VER (Red Bull Racing)"}

c1, c2, c3, c4 = st.columns(4)
with c1:
    selected_driver = st.selectbox(
        "Driver",
        options=list(driver_options.keys()),
        format_func=lambda d: driver_options[d],
    )
with c2:
    current_lap = st.slider("Current Lap Number", min_value=1, max_value=50, value=15)
with c3:
    current_compound = st.selectbox("Current Tyre Compound", options=["MEDIUM", "SOFT", "HARD"], index=0)
with c4:
    current_tyre_age = st.number_input("Current Tyre Age (Laps)", min_value=0, max_value=40, value=15)

c5, c6 = st.columns(2)
with c5:
    total_race_laps = st.number_input("Total Race Laps", min_value=30, max_value=78, value=53)
with c6:
    incremental_pit_loss = st.slider(
        "Estimated Incremental Pit Loss (seconds relative to green-flag track)",
        min_value=15.0, max_value=26.0, value=20.5, step=0.5,
    )

# Run Optimization
cost_model = StrategyCostModel(
    base_lap_time=85.0 if session_key == 9157 else 90.0,
    incremental_pit_loss=incremental_pit_loss,
)
optimizer = PitOptimizer(cost_model=cost_model)

ranked_strategies = optimizer.optimize(
    current_lap=current_lap,
    total_laps=total_race_laps,
    current_compound=current_compound,
    current_tyre_age=current_tyre_age,
    max_stops=2,
)

if not ranked_strategies:
    st.warning("No feasible strategy candidates found for the specified inputs.")
    st.stop()

best_strategy = ranked_strategies[0]

# --- Top Strategy Recommendation Card ---
st.markdown("### 🏆 Recommended Optimal Strategy")
st.success(f"**{best_strategy.name}** — Estimated Remaining Time: **{best_strategy.total_remaining_time:.2f}s**")
st.markdown(f"**Rationale:** {best_strategy.rationale}")

# --- Strategy Delta Comparison Chart ---
st.markdown("### 📊 Candidate Strategy Comparison (Delta to Optimal)")
fig_comp = plot_strategy_comparison(ranked_strategies, top_n=6)
st.plotly_chart(fig_comp, use_container_width=True)

# --- Executive Ranking Table ---
st.markdown("### 📋 Ranked Candidates Table")
df_display = PitOptimizer.to_dataframe(ranked_strategies, top_n=10)
st.dataframe(df_display, hide_index=True, use_container_width=True)

# --- Assumptions & Accounting Disclosure ---
st.markdown("### 🔍 Model Assumptions & Pit Loss Accounting")
st.markdown(f"""
- **Base Lap Time:** `{best_strategy.assumptions['base_lap_time']:.1f}s`
- **Incremental Pit Loss:** `{best_strategy.assumptions['incremental_pit_loss']:.1f}s` (defined strictly as time lost relative to staying on track).
- **Pit Loss Double-Counting Prevention:** Total pit loss added across remaining race: `{best_strategy.assumptions['pit_loss_total']:.1f}s`.
- **Compound Rules:** Minimum stint life and distinct compound requirements applied.
""")
