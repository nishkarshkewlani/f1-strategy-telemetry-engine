"""Reusable Plotly visualization components with motorsport styling."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Clean motorsport palette
DARK_BG = "#0E1117"
CARD_BG = "#161B22"
GRID_COLOR = "#21262D"
TEXT_COLOR = "#C9D1D9"
F1_RED = "#E10600"

COMPOUND_COLORS = {
    "SOFT": "#FF3333",
    "MEDIUM": "#FFD700",
    "HARD": "#FFFFFF",
    "INTERMEDIATE": "#39B54A",
    "WET": "#0072BC",
    "UNKNOWN": "#888888",
}


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply consistent motorsport dark theme to Plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color=TEXT_COLOR, family="Arial, sans-serif"),
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_COLOR)),
    )
    return fig


def plot_pace_distribution(laps_df: pd.DataFrame) -> go.Figure:
    """Violin / box plot of clean lap durations by driver."""
    clean = laps_df[laps_df["lap_duration"].notna() & (~laps_df["is_pit_out_lap"])].copy()
    fig = px.box(
        clean,
        x="name_acronym",
        y="lap_duration",
        color="team_name",
        points="outliers",
        labels={"name_acronym": "Driver", "lap_duration": "Lap Time (seconds)", "team_name": "Team"},
        title="Driver Race Pace Distribution (Green Flag)",
    )
    return apply_theme(fig)


def plot_lap_evolution(laps_df: pd.DataFrame, drivers: List[str]) -> go.Figure:
    """Lap duration time series across race laps."""
    fig = go.Figure()
    filtered = laps_df[laps_df["name_acronym"].isin(drivers)].copy()

    for drv, grp in filtered.groupby("name_acronym"):
        fig.add_trace(go.Scatter(
            x=grp["lap_number"],
            y=grp["lap_duration"],
            mode="lines+markers",
            name=drv,
            line=dict(width=2),
            marker=dict(size=4),
        ))

    fig.update_layout(
        title="Lap Time Progression Over Race Distance",
        xaxis_title="Lap Number",
        yaxis_title="Lap Duration (seconds)",
    )
    return apply_theme(fig)


def plot_telemetry_traces(telemetry_df: pd.DataFrame, driver_number: int) -> go.Figure:
    """Multi-row subplot for Speed, Throttle, Brake, Gear, RPM, and DRS."""
    if telemetry_df.empty or "driver_number" not in telemetry_df.columns:
        fig = go.Figure()
        fig.update_layout(title="No Telemetry Data Available for Selected Driver")
        return apply_theme(fig)

    df = telemetry_df[telemetry_df["driver_number"] == driver_number].copy()
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No Telemetry Data Available for Selected Driver")
        return apply_theme(fig)

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=("Speed (km/h)", "Throttle (%) & Brake (0/1)", "Engine RPM", "Gear"),
    )

    x_val = df["relative_time_sec"] if "relative_time_sec" in df.columns else np.arange(len(df))

    # Speed
    fig.add_trace(go.Scatter(x=x_val, y=df["speed"], line=dict(color="#00D2BE", width=1.5), name="Speed"), row=1, col=1)

    # Throttle & Brake
    fig.add_trace(go.Scatter(x=x_val, y=df["throttle"], line=dict(color="#00FF00", width=1.5), name="Throttle"), row=2, col=1)
    if "brake" in df.columns:
        fig.add_trace(go.Scatter(x=x_val, y=df["brake"] * 100, line=dict(color="#FF0000", width=1.5), name="Brake"), row=2, col=1)

    # RPM
    if "rpm" in df.columns:
        fig.add_trace(go.Scatter(x=x_val, y=df["rpm"], line=dict(color="#FF8700", width=1.5), name="RPM"), row=3, col=1)

    # Gear
    if "n_gear" in df.columns:
        fig.add_trace(go.Scatter(x=x_val, y=df["n_gear"], line=dict(color="#E10600", width=1.5), name="Gear"), row=4, col=1)

    fig.update_layout(height=700, title=f"Telemetry Traces - Car #{driver_number}", showlegend=False)
    fig.update_xaxes(title_text="Relative Time (seconds)", row=4, col=1)
    return apply_theme(fig)


def plot_stint_timeline(stints_df: pd.DataFrame) -> go.Figure:
    """Gantt-style stint visualization showing tyre compound usage across laps."""
    fig = go.Figure()
    drivers = sorted(stints_df["name_acronym"].unique())

    for idx, drv in enumerate(drivers):
        drv_stints = stints_df[stints_df["name_acronym"] == drv].sort_values("stint_number")
        for _, s in drv_stints.iterrows():
            comp = str(s["compound"]).upper()
            color = COMPOUND_COLORS.get(comp, "#888888")
            start = s["lap_start"]
            length = s["lap_end"] - s["lap_start"] + 1

            fig.add_trace(go.Bar(
                y=[drv],
                x=[length],
                base=start - 1,
                orientation="h",
                name=comp,
                marker=dict(color=color, line=dict(color="#111", width=1)),
                hovertext=f"{drv} | Stint {s['stint_number']}: {comp} (Laps {start}-{s['lap_end']})",
                showlegend=False,
            ))

    fig.update_layout(
        title="Tyre Stint Timeline by Driver",
        xaxis_title="Lap Number",
        yaxis_title="Driver",
        barmode="stack",
        height=550,
    )
    return apply_theme(fig)


def plot_tyre_degradation(stints_with_pace: pd.DataFrame) -> go.Figure:
    """Plot pace against tyre age in laps grouped by compound."""
    clean = stints_with_pace[
        (~stints_with_pace["is_pit_out_lap"]) & (stints_with_pace["lap_duration"].notna())
    ].copy()

    fig = px.scatter(
        clean,
        x="tyre_age",
        y="lap_duration",
        color="compound",
        color_discrete_map=COMPOUND_COLORS,
        trendline="ols",
        labels={"tyre_age": "Tyre Age (laps in stint)", "lap_duration": "Lap Time (seconds)"},
        title="Tyre Age vs Lap Pace (Observed Degradation Slopes)",
        opacity=0.6,
    )
    return apply_theme(fig)


def plot_strategy_comparison(candidates: List[Any], top_n: int = 5) -> go.Figure:
    """Bar chart comparing total remaining race time across candidate strategies."""
    top = candidates[:top_n]
    names = [c.name for c in top]
    times = [c.total_remaining_time for c in top]
    deltas = [c.delta_to_best for c in top]

    colors = [F1_RED if d == 0 else "#3E4C59" for d in deltas]

    fig = go.Figure(go.Bar(
        x=deltas,
        y=names,
        orientation="h",
        marker=dict(color=colors),
        text=[f"+{d:.2f}s" if d > 0 else "0.00s (Optimal)" for d in deltas],
        textposition="outside",
    ))

    fig.update_layout(
        title=f"Top {len(top)} Candidate Strategies (Delta to Optimal)",
        xaxis_title="Delta to Optimal Strategy (seconds)",
        yaxis=dict(autorange="reversed"),
        height=350,
    )
    return apply_theme(fig)
