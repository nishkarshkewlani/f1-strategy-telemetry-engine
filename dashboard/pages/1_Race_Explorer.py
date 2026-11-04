"""Race Explorer: Pace distributions, lap progression, and sector bests."""

from pathlib import Path
import sys
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from analysis.lap_analysis import LapAnalyzer
from dashboard.components import plot_lap_evolution, plot_pace_distribution
from database.repository import F1Repository

st.set_page_config(page_title="Race Explorer - F1 Strategy Engine", page_icon="🏎️", layout="wide")

repo = F1Repository()
analyzer = LapAnalyzer(repo)

session_key = st.session_state.get("selected_session_key")
if not session_key:
    sessions = repo.get_all_sessions()
    if not sessions.empty:
        session_key = int(sessions.iloc[0]["session_key"])
    else:
        st.error("No sessions available.")
        st.stop()

st.title("⏱️ Race & Pace Explorer")
st.caption(f"Session Key: `{session_key}` | Analyzing Green-Flag Lap Durations and Sector Splits")

laps_df = repo.get_laps(session_key)
if laps_df.empty:
    st.warning("No lap timing records found for this session.")
    st.stop()

# 1. Pace Distribution Box Plot
st.markdown("### 📊 Driver Green-Flag Pace Distributions")
fig_box = plot_pace_distribution(laps_df)
st.plotly_chart(fig_box, use_container_width=True)

# 2. Lap Progression Chart
st.markdown("### 📈 Lap Time Progression Across Race Distance")
available_drivers = sorted(laps_df["name_acronym"].dropna().unique().tolist())
default_drivers = available_drivers[:3] if len(available_drivers) >= 3 else available_drivers

selected_drivers = st.multiselect(
    "Select Drivers to Compare:",
    options=available_drivers,
    default=default_drivers,
)

if selected_drivers:
    fig_line = plot_lap_evolution(laps_df, selected_drivers)
    st.plotly_chart(fig_line, use_container_width=True)

# 3. Consistency Index & Sector Bests
st.markdown("### 🎯 Driver Consistency & Theoretical Optimal Laps")
tab1, tab2 = st.tabs(["Consistency Index", "Sector Bests & Theoretical Lap"])

with tab1:
    consistency_df = analyzer.calculate_driver_consistency(session_key)
    if not consistency_df.empty:
        st.dataframe(
            consistency_df.rename(columns={
                "name_acronym": "Driver",
                "team_name": "Constructor",
                "clean_laps_count": "Clean Laps",
                "median_pace": "Median Pace (s)",
                "mean_pace": "Mean Pace (s)",
                "std_pace": "Std Dev (s)",
                "fastest_lap": "Best Lap (s)",
                "iqr_pace": "IQR Consistency (s)",
            }),
            hide_index=True,
            use_container_width=True,
        )

with tab2:
    with open(BASE_DIR / "sql_queries" / "sector_bests.sql", "r", encoding="utf-8") as f:
        sector_sql = f.read()
    sectors_df = repo.execute_custom_sql(sector_sql, params={"session_key": session_key})
    if not sectors_df.empty:
        st.dataframe(
            sectors_df.rename(columns={
                "name_acronym": "Driver",
                "team_name": "Constructor",
                "best_s1": "Best S1 (s)",
                "best_s2": "Best S2 (s)",
                "best_s3": "Best S3 (s)",
                "theoretical_best_lap": "Theoretical Lap (s)",
                "actual_fastest_lap": "Actual Fastest (s)",
                "theoretical_delta": "Theoretical Delta (s)",
            }),
            hide_index=True,
            use_container_width=True,
        )
