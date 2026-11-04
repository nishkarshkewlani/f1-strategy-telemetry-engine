"""High-Frequency Telemetry Analyzer: Speed, Throttle, Brake, RPM, Gear, DRS."""

from pathlib import Path
import sys
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from analysis.telemetry_analysis import TelemetryAnalyzer
from dashboard.components import plot_telemetry_traces
from database.repository import F1Repository

st.set_page_config(page_title="Telemetry Analyzer - F1 Strategy Engine", page_icon="🏎️", layout="wide")

repo = F1Repository()
analyzer = TelemetryAnalyzer(repo)

session_key = st.session_state.get("selected_session_key")
if not session_key:
    sessions = repo.get_all_sessions()
    if not sessions.empty:
        session_key = int(sessions.iloc[0]["session_key"])
    else:
        st.error("No sessions available.")
        st.stop()

st.title("📡 High-Frequency Telemetry Analyzer")
st.caption(f"Session Key: `{session_key}` | Inspecting Sensor Time Traces")

drivers_df = repo.get_drivers_by_session(session_key)
if drivers_df.empty:
    st.warning("No driver records found for this session.")
    st.stop()

driver_options = {
    int(row["driver_number"]): f"#{row['driver_number']} {row['name_acronym']} ({row['team_name']})"
    for _, row in drivers_df.iterrows()
}

selected_driver = st.selectbox(
    "Select Driver for High-Frequency Analysis:",
    options=list(driver_options.keys()),
    format_func=lambda d: driver_options[d],
)

telemetry_df = analyzer.get_driver_telemetry(session_key=session_key, driver_number=selected_driver)

if telemetry_df.empty:
    st.info(f"High-frequency telemetry was not ingested for driver #{selected_driver} to respect API storage limits. Telemetry is available for drivers ingested during the session harvest (e.g. #1 Verstappen, #2 Sargeant).")
else:
    st.markdown("### 🏎️ Sensor Traces")
    fig_traces = plot_telemetry_traces(telemetry_df, selected_driver)
    st.plotly_chart(fig_traces, use_container_width=True)

    # Telemetry Summary KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Max Speed Recorded", f"{telemetry_df['speed'].max():.1f} km/h")
    kpi2.metric("Avg Speed", f"{telemetry_df['speed'].mean():.1f} km/h")
    kpi3.metric("Max Engine RPM", f"{telemetry_df['rpm'].max():.0f} RPM" if 'rpm' in telemetry_df else "N/A")
    kpi4.metric("Samples Logged", f"{len(telemetry_df):,}")
