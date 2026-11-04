"""Race Scenario Engine: Baseline vs Safety Car, Weather, and Sensitivity Sweeps."""

import copy
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from strategy.cost_model import CandidateStrategy, StrategyCostModel
from strategy.pit_optimizer import PitOptimizer

logger = logging.getLogger(__name__)


class ScenarioSimulator:
    """Simulates what-if scenarios and sensitivity parameters."""

    def __init__(self, optimizer: Optional[PitOptimizer] = None):
        self.optimizer = optimizer or PitOptimizer()

    def run_scenario_comparison(
        self,
        current_lap: int,
        total_laps: int,
        current_compound: str,
        current_tyre_age: int,
        sc_lap_start: Optional[int] = None,
        sc_duration: int = 3,
        rain_lap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compare Baseline (green flag) vs Safety Car vs Weather scenarios."""
        # 1. Baseline Run
        baseline_candidates = self.optimizer.optimize(
            current_lap=current_lap,
            total_laps=total_laps,
            current_compound=current_compound,
            current_tyre_age=current_tyre_age,
            sc_window=None,
            weather_rain_lap=None,
        )

        sc_window = None
        if sc_lap_start:
            sc_window = list(range(sc_lap_start, min(total_laps, sc_lap_start + sc_duration)))

        # 2. Safety Car Scenario Run
        sc_candidates = self.optimizer.optimize(
            current_lap=current_lap,
            total_laps=total_laps,
            current_compound=current_compound,
            current_tyre_age=current_tyre_age,
            sc_window=sc_window,
            weather_rain_lap=None,
        ) if sc_window else []

        # 3. Weather Scenario Run
        weather_candidates = self.optimizer.optimize(
            current_lap=current_lap,
            total_laps=total_laps,
            current_compound=current_compound,
            current_tyre_age=current_tyre_age,
            allowed_compounds=["INTERMEDIATE", "WET", "HARD", "MEDIUM"],
            sc_window=sc_window,
            weather_rain_lap=rain_lap,
        ) if rain_lap else []

        return {
            "baseline_best": baseline_candidates[0] if baseline_candidates else None,
            "baseline_top5": baseline_candidates[:5] if baseline_candidates else [],
            "sc_window": sc_window,
            "sc_best": sc_candidates[0] if sc_candidates else None,
            "sc_top5": sc_candidates[:5] if sc_candidates else [],
            "rain_lap": rain_lap,
            "weather_best": weather_candidates[0] if weather_candidates else None,
            "weather_top5": weather_candidates[:5] if weather_candidates else [],
        }

    def run_sensitivity_sweep(
        self,
        current_lap: int,
        total_laps: int,
        current_compound: str,
        current_tyre_age: int,
        pit_loss_deltas: List[float] = [-3.0, 0.0, +3.0],
        deg_multipliers: List[float] = [0.8, 1.0, 1.25],
    ) -> pd.DataFrame:
        """Evaluate strategy robustness across varying pit loss and tyre wear rates."""
        records = []
        base_cost_model = self.optimizer.cost_model

        for p_delta in pit_loss_deltas:
            for d_mult in deg_multipliers:
                # Build modified parameters
                custom_pit_loss = base_cost_model.incremental_pit_loss + p_delta
                custom_compounds = copy.deepcopy(base_cost_model.compound_params)
                for comp in custom_compounds:
                    custom_compounds[comp]["degradation_per_lap"] *= d_mult

                swept_model = StrategyCostModel(
                    base_lap_time=base_cost_model.base_lap_time,
                    incremental_pit_loss=custom_pit_loss,
                    sc_pit_loss=base_cost_model.sc_pit_loss,
                    compound_params=custom_compounds,
                )
                swept_optimizer = PitOptimizer(cost_model=swept_model)
                candidates = swept_optimizer.optimize(
                    current_lap=current_lap,
                    total_laps=total_laps,
                    current_compound=current_compound,
                    current_tyre_age=current_tyre_age,
                )

                if candidates:
                    top = candidates[0]
                    records.append({
                        "Pit Loss (s)": round(custom_pit_loss, 1),
                        "Deg Multiplier": f"{d_mult:.2f}x",
                        "Optimal Strategy": top.name,
                        "Pit Laps": ", ".join(map(str, top.pit_laps)),
                        "Est. Time (s)": round(top.total_remaining_time, 2),
                    })

        return pd.DataFrame(records)
