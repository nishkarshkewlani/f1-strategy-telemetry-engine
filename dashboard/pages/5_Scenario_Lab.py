"""Scenario Lab: Safety Car, Changing Weather, and Sensitivity Sweeps."""

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
from strategy.scenario_simulator import ScenarioSimulator

st.set_page_config(page_title="Scenario Lab - F1 Strategy Engine", page_icon="🏎️", layout="wide")

repo = F1Repository()

session_key = st.session_state.get("selected_session_key")
if not session_key:
    sessions = repo.get_all_sessions()
    if not sessions.empty:
        session_key = int(sessions.iloc[0]["session_key"])
    else:
        st.error("No sessions available.")
        st.stop()

st.title("🔬 Scenario Lab & What-If Simulator")
st.caption("Stress-test pit decisions against Safety Cars, Weather Transitions, and Sensitivity Sweeps")

# Simulator Controls
st.markdown("### 🎛️ Simulation Parameters")
col1, col2, col3 = st.columns(3)

with col1:
    current_lap = st.slider("Current Lap", min_value=1, max_value=45, value=15)
    total_laps = st.number_input("Total Laps", min_value=30, max_value=70, value=53)
with col2:
    enable_sc = st.checkbox("Simulate Safety Car Window", value=True)
    sc_start = st.slider("Safety Car Start Lap", min_value=current_lap + 1, max_value=total_laps - 2, value=min(current_lap + 5, total_laps - 2)) if enable_sc else None
    sc_duration = st.slider("Safety Car Duration (laps)", min_value=2, max_value=6, value=3) if enable_sc else 0
with col3:
    enable_rain = st.checkbox("Simulate Rain / Weather Transition", value=False)
    rain_lap = st.slider("Rain Arrival Lap", min_value=current_lap + 1, max_value=total_laps - 1, value=min(current_lap + 10, total_laps - 1)) if enable_rain else None

cost_model = StrategyCostModel(base_lap_time=85.0 if session_key == 9157 else 90.0)
optimizer = PitOptimizer(cost_model=cost_model)
simulator = ScenarioSimulator(optimizer=optimizer)

results = simulator.run_scenario_comparison(
    current_lap=current_lap,
    total_laps=total_laps,
    current_compound="MEDIUM",
    current_tyre_age=current_lap,
    sc_lap_start=sc_start,
    sc_duration=sc_duration,
    rain_lap=rain_lap,
)

# --- Side-by-Side Comparison ---
st.markdown("### ⚖️ Side-by-Side Scenario Outcomes")
sc_col1, sc_col2 = st.columns(2)

with sc_col1:
    st.markdown("#### 🟢 Baseline (Green Flag)")
    if results["baseline_best"]:
        b_best = results["baseline_best"]
        st.info(f"**Optimal:** {b_best.name}\n\n**Time:** {b_best.total_remaining_time:.2f}s")
        st.write(f"Rationale: {b_best.rationale}")
        fig_b = plot_strategy_comparison(results["baseline_top5"], top_n=4)
        st.plotly_chart(fig_b, use_container_width=True)

with sc_col2:
    if enable_sc and results["sc_best"]:
        st.markdown(f"#### 🟡 Safety Car (Laps {results['sc_window'][0]}-{results['sc_window'][-1]})")
        sc_best = results["sc_best"]
        st.warning(f"**Optimal:** {sc_best.name}\n\n**Time:** {sc_best.total_remaining_time:.2f}s")
        st.write(f"Rationale: {sc_best.rationale}")
        fig_sc = plot_strategy_comparison(results["sc_top5"], top_n=4)
        st.plotly_chart(fig_sc, use_container_width=True)
    elif enable_rain and results["weather_best"]:
        st.markdown(f"#### 🌧️ Wet Track (Rain on Lap {results['rain_lap']})")
        w_best = results["weather_best"]
        st.info(f"**Optimal:** {w_best.name}\n\n**Time:** {w_best.total_remaining_time:.2f}s")
        st.write(f"Rationale: {w_best.rationale}")
        fig_w = plot_strategy_comparison(results["weather_top5"], top_n=4)
        st.plotly_chart(fig_w, use_container_width=True)
    else:
        st.info("Enable Safety Car or Weather to observe dynamic scenario shifts.")

# --- Robustness & Sensitivity Sweep Matrix ---
st.markdown("### 📈 Strategy Sensitivity Matrix")
st.caption("Verifying decision stability across varying pit loss penalties and tyre degradation rates")

df_sweep = simulator.run_sensitivity_sweep(
    current_lap=current_lap,
    total_laps=total_laps,
    current_compound="MEDIUM",
    current_tyre_age=current_lap,
    pit_loss_deltas=[-3.0, 0.0, +3.0],
    deg_multipliers=[0.8, 1.0, 1.25],
)
st.dataframe(df_sweep, hide_index=True, use_container_width=True)
