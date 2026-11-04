"""F1 Strategy & Telemetry Engine - Main Dashboard Entry Point & Race Overview."""

import os
import sys
from pathlib import Path
import streamlit as st

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.repository import F1Repository
from dashboard.components import apply_theme

# Streamlit Page Config
st.set_page_config(
    page_title="F1 Strategy & Telemetry Engine",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern motorsport dark theme
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #C9D1D9;
    }
    .metric-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: bold;
        color: #E10600;
    }
    .metric-label {
        font-size: 13px;
        color: #8B949E;
        text-transform: uppercase;
    }
    .disclaimer-box {
        background-color: #1F242C;
        border-left: 4px solid #E10600;
        padding: 12px 16px;
        border-radius: 4px;
        margin-top: 20px;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_repository() -> F1Repository:
    return F1Repository()


repo = get_repository()

# --- SIDEBAR: Session & Global Filters ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/3/33/F1.svg", width=120)
st.sidebar.title("Telemetry Engine")
st.sidebar.markdown("**Decision-Support Platform**")

sessions_df = repo.get_all_sessions()

if sessions_df.empty:
    st.error("No race data found in the relational database. Please ingest sessions into the database first.")
    st.stop()

# Format session options
session_options = {}
for _, row in sessions_df.iterrows():
    s_key = int(row["session_key"])
    c_name = row.get("circuit_short_name", "Grand Prix")
    yr = row.get("year", 2023)
    s_name = row.get("session_name", "Race")
    session_options[s_key] = f"{yr} {c_name} - {s_name} (Key: {s_key})"

selected_session_key = st.sidebar.selectbox(
    "Select Race Session",
    options=list(session_options.keys()),
    format_func=lambda k: session_options[k],
)

# Store selected session in session_state for multipage synchronization
st.session_state["selected_session_key"] = selected_session_key

session_info = sessions_df[sessions_df["session_key"] == selected_session_key].iloc[0]
circuit = session_info.get("circuit_short_name", "Grand Prix")
year = session_info.get("year", 2023)
country = session_info.get("country_name", "")

# --- MAIN CONTENT: Home / Race Overview ---
st.title(f"🏎️ {year} {circuit} Grand Prix")
st.caption(f"Session Key: `{selected_session_key}` | Location: {country} | Relational Source: OpenF1 Primary")

# 1. Key Metrics Ribbon
drivers_df = repo.get_drivers_by_session(selected_session_key)
laps_df = repo.get_laps(selected_session_key)
stints_df = repo.get_stints(selected_session_key)
pits_df = repo.get_pit_stops(selected_session_key)
weather_df = repo.get_weather(selected_session_key)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown('<div class="metric-card"><div class="metric-label">Drivers on Grid</div>'
                f'<div class="metric-value">{len(drivers_df)}</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card"><div class="metric-label">Laps Recorded</div>'
                f'<div class="metric-value">{len(laps_df)}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card"><div class="metric-label">Tyre Stints</div>'
                f'<div class="metric-value">{len(stints_df)}</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown('<div class="metric-card"><div class="metric-label">Pit Stops</div>'
                f'<div class="metric-value">{len(pits_df)}</div></div>', unsafe_allow_html=True)
with col5:
    clean_laps = laps_df[laps_df["lap_duration"].notna() & (~laps_df["is_pit_out_lap"])]
    fastest_time = clean_laps["lap_duration"].min() if not clean_laps.empty else None
    display_time = f"{fastest_time:.3f}s" if fastest_time else "N/A"
    st.markdown('<div class="metric-card"><div class="metric-label">Fastest Lap</div>'
                f'<div class="metric-value">{display_time}</div></div>', unsafe_allow_html=True)

# 2. Driver & Team Grid
st.markdown("### 📋 Participating Drivers & Constructors")
if not drivers_df.empty:
    display_cols = ["driver_number", "broadcast_name", "name_acronym", "team_name"]
    cols_present = [c for c in display_cols if c in drivers_df.columns]
    renamed = drivers_df[cols_present].rename(columns={
        "driver_number": "Car #",
        "broadcast_name": "Driver",
        "name_acronym": "Code",
        "team_name": "Constructor",
    })
    st.dataframe(renamed, hide_index=True, use_container_width=True)
else:
    st.info("No drivers recorded for this session.")

# 3. Environmental & Track Conditions
st.markdown("### ⛅ Track & Ambient Weather Progression")
if not weather_df.empty:
    w_cols = st.columns(4)
    w_cols[0].metric("Avg Track Temp", f"{weather_df['track_temperature'].mean():.1f} °C")
    w_cols[1].metric("Avg Air Temp", f"{weather_df['air_temperature'].mean():.1f} °C")
    w_cols[2].metric("Avg Humidity", f"{weather_df['humidity'].mean():.1f} %")
    w_cols[3].metric("Avg Wind Speed", f"{weather_df['wind_speed'].mean():.1f} km/h")
else:
    st.info("Weather data is not available for this session.")

# 4. Scope & Educational Transparency Disclaimer
st.markdown("""
<div class="disclaimer-box">
    <strong>Decision-Support Scope & Assumptions:</strong><br>
    This platform transforms historical timing, telemetry, tyre stint, and race control data into explainable strategy recommendations. 
    Public telemetry and timing feeds operate within documented sampling limits and omit proprietary variables such as live fuel load, 
    internal tyre temperatures, and confidential team CFD models. All strategy recommendations are simulated estimates under explicit 
    assumptions and empirical uncertainty intervals.
</div>
""", unsafe_allow_html=True)
