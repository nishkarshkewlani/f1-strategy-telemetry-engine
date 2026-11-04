"""Unit tests for strategy optimization, pit loss accounting, and scenario simulator."""

import pytest
from strategy.candidate_generator import CandidateGenerator
from strategy.cost_model import CandidateStrategy, StintPlan, StrategyCostModel
from strategy.pit_optimizer import PitOptimizer
from strategy.scenario_simulator import ScenarioSimulator


def test_pit_loss_accounting_no_double_counting():
    """Verify incremental pit loss is added exactly once per pit stop."""
    cost_model = StrategyCostModel(
        base_lap_time=90.0,
        incremental_pit_loss=20.0,
    )

    strat = CandidateStrategy(
        name="Test 1-Stop",
        stints=[
            StintPlan("MEDIUM", 1, 15, 0),
            StintPlan("HARD", 16, 30, 0),
        ],
        pit_laps=[15],
    )

    evaluated = cost_model.evaluate_strategy(strat, current_lap=0, total_laps=30)
    # Total pit loss added must be exactly 20.0s (not full pit lane time + on-track time)
    assert evaluated.assumptions["pit_loss_total"] == 20.0
    assert evaluated.total_remaining_time > (30 * 85.0)


def test_safety_car_scenario_recalculation():
    """Verify safety car window uses reduced pit loss and rewards pitting under SC versus under green flag."""
    cost_model = StrategyCostModel(
        base_lap_time=85.0,
        incremental_pit_loss=20.5,
        sc_pit_loss=11.0,
    )

    # Strategy pitting under green flag at lap 30 (while SC occurred earlier at laps 19-21)
    strat_pit_under_green = CandidateStrategy(
        name="Lap 30 Stop Green",
        stints=[StintPlan("MEDIUM", 1, 30, 0), StintPlan("HARD", 31, 50, 0)],
        pit_laps=[30],
    )
    res_green_stop = cost_model.evaluate_strategy(
        strat_pit_under_green, current_lap=10, total_laps=50, sc_window=[19, 20, 21]
    )
    # Pitting at lap 30 is outside the SC window, so pays full green-flag pit loss
    assert res_green_stop.assumptions["pit_loss_total"] == 20.5

    # Strategy pitting during Safety Car at lap 20
    strat_pit_under_sc = CandidateStrategy(
        name="Lap 20 Stop SC",
        stints=[StintPlan("MEDIUM", 1, 20, 0), StintPlan("HARD", 21, 50, 0)],
        pit_laps=[20],
    )
    res_sc_stop = cost_model.evaluate_strategy(
        strat_pit_under_sc, current_lap=10, total_laps=50, sc_window=[19, 20, 21]
    )
    # Under SC, pit loss drops to 11.0s
    assert res_sc_stop.assumptions["pit_loss_total"] == 11.0

    # Pitting under SC gains ~9.5s on pit entry compared to waiting for green flag
    assert res_sc_stop.assumptions["pit_loss_total"] < res_green_stop.assumptions["pit_loss_total"]


def test_optimizer_ranks_deterministic_candidates():
    """Verify optimizer returns ranked candidates with delta_to_best >= 0."""
    optimizer = PitOptimizer()
    ranked = optimizer.optimize(
        current_lap=10,
        total_laps=50,
        current_compound="MEDIUM",
        current_tyre_age=10,
        max_stops=1,
    )

    assert len(ranked) > 0
    # Top rank must have delta 0.0
    assert ranked[0].delta_to_best == 0.0
    assert ranked[0].rationale != ""

    # Successive ranks must have non-decreasing total time
    for i in range(len(ranked) - 1):
        assert ranked[i].total_remaining_time <= ranked[i + 1].total_remaining_time


def test_sensitivity_sweep_runs():
    """Verify sensitivity matrix evaluates variations in pit loss and degradation."""
    sim = ScenarioSimulator()
    df_sweep = sim.run_sensitivity_sweep(
        current_lap=15,
        total_laps=50,
        current_compound="MEDIUM",
        current_tyre_age=15,
        pit_loss_deltas=[-3.0, 0.0],
        deg_multipliers=[0.8, 1.2],
    )
    assert len(df_sweep) == 4
    assert "Optimal Strategy" in df_sweep.columns
    assert "Est. Time (s)" in df_sweep.columns
