"""Unit tests for dashboard components and visualization helpers."""

import numpy as np
import pandas as pd
import pytest
from dashboard.components import (
    plot_lap_evolution,
    plot_pace_distribution,
    plot_stint_timeline,
    plot_strategy_comparison,
    plot_telemetry_traces,
    plot_tyre_degradation,
)
from strategy.cost_model import CandidateStrategy, StintPlan


def test_plot_pace_distribution_renders():
    df = pd.DataFrame({
        "name_acronym": ["VER", "VER", "HAM", "HAM"],
        "team_name": ["Red Bull", "Red Bull", "Mercedes", "Mercedes"],
        "lap_duration": [85.5, 85.8, 86.2, 86.0],
        "is_pit_out_lap": [False, False, False, False],
    })
    fig = plot_pace_distribution(df)
    assert fig is not None
    assert len(fig.data) > 0


def test_plot_telemetry_traces_empty_and_valid():
    # Empty
    empty_df = pd.DataFrame()
    fig_empty = plot_telemetry_traces(empty_df, driver_number=1)
    assert fig_empty is not None

    # Valid
    df = pd.DataFrame({
        "driver_number": [1, 1, 1],
        "relative_time_sec": [0.0, 0.1, 0.2],
        "speed": [310.0, 312.0, 314.0],
        "throttle": [100.0, 100.0, 100.0],
        "brake": [0.0, 0.0, 0.0],
        "rpm": [11500, 11600, 11700],
        "n_gear": [8, 8, 8],
        "drs": [1, 1, 1],
    })
    fig = plot_telemetry_traces(df, driver_number=1)
    assert fig is not None
    assert len(fig.data) >= 4


def test_plot_strategy_comparison():
    cands = [
        CandidateStrategy(
            name="1-Stop Medium->Hard",
            stints=[StintPlan("MEDIUM", 1, 20, 0), StintPlan("HARD", 21, 53, 0)],
            total_remaining_time=3200.5,
            delta_to_best=0.0,
        ),
        CandidateStrategy(
            name="2-Stop Soft->Hard->Soft",
            stints=[StintPlan("SOFT", 1, 15, 0), StintPlan("HARD", 16, 38, 0), StintPlan("SOFT", 39, 53, 0)],
            total_remaining_time=3215.2,
            delta_to_best=14.7,
        ),
    ]
    fig = plot_strategy_comparison(cands, top_n=2)
    assert fig is not None
    assert len(fig.data) == 1
