"""Pit-stop strategy ranking, optimizer, and plain-language explanation generator."""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from strategy.candidate_generator import CandidateGenerator
from strategy.cost_model import CandidateStrategy, StrategyCostModel

logger = logging.getLogger(__name__)


class PitOptimizer:
    """Evaluates candidate strategies, ranks outcomes, and provides explainable rationale."""

    def __init__(self, cost_model: Optional[StrategyCostModel] = None):
        self.cost_model = cost_model or StrategyCostModel()
        self.generator = CandidateGenerator(compound_params=self.cost_model.compound_params)

    def optimize(
        self,
        current_lap: int,
        total_laps: int,
        current_compound: str,
        current_tyre_age: int,
        allowed_compounds: Optional[List[str]] = None,
        max_stops: int = 2,
        sc_window: Optional[List[int]] = None,
        weather_rain_lap: Optional[int] = None,
    ) -> List[CandidateStrategy]:
        """Generate, evaluate, and rank candidate strategies."""
        candidates = self.generator.generate_candidates(
            current_lap=current_lap,
            total_laps=total_laps,
            current_compound=current_compound,
            current_tyre_age=current_tyre_age,
            allowed_replacement_compounds=allowed_compounds,
            max_stops=max_stops,
        )

        if not candidates:
            return []

        # Evaluate all candidate costs
        evaluated: List[CandidateStrategy] = []
        for cand in candidates:
            scored = self.cost_model.evaluate_strategy(
                strategy=cand,
                current_lap=current_lap,
                total_laps=total_laps,
                sc_window=sc_window,
                weather_rain_lap=weather_rain_lap,
            )
            evaluated.append(scored)

        # Sort ascending by total remaining time
        evaluated.sort(key=lambda x: x.total_remaining_time)

        # Compute delta to best
        best_time = evaluated[0].total_remaining_time
        for rank, cand in enumerate(evaluated, start=1):
            cand.delta_to_best = round(cand.total_remaining_time - best_time, 3)

        # Generate plain-language rationale for top choice
        best = evaluated[0]
        stints_desc = " -> ".join([f"{s.compound} ({s.lap_count} laps)" for s in best.stints])
        sc_note = f" (capitalizes on Safety Car window at laps {sc_window})" if sc_window else ""
        rain_note = f" (adapts to rain starting on lap {weather_rain_lap})" if weather_rain_lap else ""

        if len(best.pit_laps) == 1:
            best.rationale = (
                f"Rank 1: 1-Stop strategy pitting on Lap {best.pit_laps[0]} with sequence {stints_desc}. "
                f"Balances tyre degradation against the ~{self.cost_model.incremental_pit_loss}s incremental pit loss "
                f"without incurring an extra pit stop{sc_note}{rain_note}."
            )
        else:
            best.rationale = (
                f"Rank 1: 2-Stop strategy pitting on Laps {best.pit_laps} with sequence {stints_desc}. "
                f"Higher pace on fresh rubber offsets the second pit stop loss{sc_note}{rain_note}."
            )

        return evaluated

    @staticmethod
    def to_dataframe(ranked_candidates: List[CandidateStrategy], top_n: int = 10) -> pd.DataFrame:
        """Format ranked candidate strategies into an executive display table."""
        rows = []
        for rank, s in enumerate(ranked_candidates[:top_n], start=1):
            pit_str = ", ".join(map(str, s.pit_laps)) if s.pit_laps else "None"
            compound_seq = " -> ".join([st.compound for st in s.stints])
            rows.append({
                "Rank": rank,
                "Strategy": s.name,
                "Pit Lap(s)": pit_str,
                "Compounds": compound_seq,
                "Est. Remaining Time": f"{s.total_remaining_time:.2f}s",
                "Delta to Best": f"+{s.delta_to_best:.2f}s" if s.delta_to_best > 0 else "0.00s (Best)",
            })
        return pd.DataFrame(rows)
