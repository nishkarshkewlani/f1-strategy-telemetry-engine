"""Tyre Analytics: Stint timeline, compound degradation slopes, and stint summaries."""

from pathlib import Path
import sys
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from analysis.tyre_analysis import TyreAnalyzer
from dashboard.components import plot_stint_timeline, plot_tyre_degradation
from database.repository import F1Repository

st.set_page_config(page_title="Tyre Analytics - F1 Strategy Engine", page_icon="🏎️", layout="wide")

repo = F1Repository()
analyzer = TyreAnalyzer(repo)

session_key = st.session_state.get("selected_session_key")
if not session_key:
    sessions = repo.get_all_sessions()
    if not sessions.empty:
        session_key = int(sessions.iloc[0]["session_key"])
    else:
        st.error("No sessions available.")
        st.stop()

st.title("🛞 Tyre Degradation & Stint Analytics")
st.caption(f"Session Key: `{session_key}` | Lap-to-Stint Mapping and Empirical Degradation Models")

stints_df = repo.get_stints(session_key)
if stints_df.empty:
    st.warning("No tyre stint records found for this session.")
    st.stop()

# 1. Stint Timeline
st.markdown("### 🏁 Tyre Stint Timeline (Compound Strategy by Driver)")
fig_timeline = plot_stint_timeline(stints_df)
st.plotly_chart(fig_timeline, use_container_width=True)

# 2. Tyre Degradation Curves
st.markdown("### 📉 Observed Pace Degradation Curves")
stints_with_pace = analyzer.get_stints_with_pace(session_key)

if not stints_with_pace.empty:
    fig_deg = plot_tyre_degradation(stints_with_pace)
    st.plotly_chart(fig_deg, use_container_width=True)
else:
    st.info("Unable to merge lap timing with tyre stints for degradation plotting.")

# 3. Compound Degradation Estimates Table
st.markdown("### 🧪 Empirical Degradation Slopes by Compound")
deg_summary = analyzer.estimate_compound_degradation(session_key)
if not deg_summary.empty:
    st.dataframe(
        deg_summary.rename(columns={
            "compound": "Compound",
            "laps_observed": "Laps Observed",
            "drivers_represented": "Drivers Count",
            "base_pace_seconds": "Fresh Pace Intercept (s)",
            "degradation_sec_per_lap": "Degradation Rate (s/lap)",
            "max_tyre_age_observed": "Max Age (laps)",
        }),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("Insufficient clean stint data to compute linear degradation slopes.")

st.info(
    "💡 **Motorsport Note:** Degradation slopes reflect empirical lap time loss per lap of tyre age. "
    "Values account for race track context and exclude pit-in and pit-out laps."
)
