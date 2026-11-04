"""Candidate strategy generator for 1-stop and 2-stop race scenarios."""

import logging
from typing import Dict, List, Optional
from strategy.cost_model import CandidateStrategy, DEFAULT_COMPOUND_PARAMS, StintPlan

logger = logging.getLogger(__name__)


class CandidateGenerator:
    """Generates physically feasible candidate pit stop strategies."""

    def __init__(self, compound_params: Optional[Dict[str, Dict[str, float]]] = None):
        self.compound_params = compound_params or DEFAULT_COMPOUND_PARAMS

    def generate_candidates(
        self,
        current_lap: int,
        total_laps: int,
        current_compound: str,
        current_tyre_age: int,
        allowed_replacement_compounds: Optional[List[str]] = None,
        max_stops: int = 2,
    ) -> List[CandidateStrategy]:
        """Generate feasible 1-stop and 2-stop strategies."""
        replacements = allowed_replacement_compounds or ["HARD", "MEDIUM", "SOFT"]
        candidates: List[CandidateStrategy] = []

        remaining_laps = total_laps - current_lap
        if remaining_laps <= 0:
            return []

        # -------------------------------------------------------------
        # 1-STOP CANDIDATES: Pit at lap P (from current_lap + 1 to total_laps - 3)
        # -------------------------------------------------------------
        # Generate pit laps every 2-3 laps to cover the pit window
        min_pit_lap = max(current_lap + 1, 10)
        max_pit_lap = total_laps - 5

        pit_step = 2 if (max_pit_lap - min_pit_lap) <= 20 else 3
        pit_lap_range = list(range(min_pit_lap, max_pit_lap + 1, pit_step))

        for pit_lap in pit_lap_range:
            stint1_length = pit_lap - current_lap
            stint1_total_age = current_tyre_age + stint1_length

            # Check if current tyre can reach pit lap
            current_max_life = self.compound_params.get(current_compound, {}).get("max_life", 45)
            if stint1_total_age > current_max_life:
                continue

            for next_comp in replacements:
                # Sporting regulation: must change compound in dry race if starting stint had dry compound
                if next_comp == current_compound and remaining_laps > 20:
                    continue  # Require distinct compound for dry 1-stop

                stint2_length = total_laps - pit_lap
                next_max_life = self.compound_params.get(next_comp, {}).get("max_life", 45)
                if stint2_length > next_max_life:
                    continue  # Stint 2 exceeds tyre life

                stint1 = StintPlan(
                    compound=current_compound,
                    lap_start=current_lap,
                    lap_end=pit_lap,
                    starting_tyre_age=current_tyre_age,
                )
                stint2 = StintPlan(
                    compound=next_comp,
                    lap_start=pit_lap + 1,
                    lap_end=total_laps,
                    starting_tyre_age=0,
                )

                strat_name = f"1-Stop: L{pit_lap} -> {next_comp}"
                candidates.append(
                    CandidateStrategy(
                        name=strat_name,
                        stints=[stint1, stint2],
                        pit_laps=[pit_lap],
                    )
                )

        # -------------------------------------------------------------
        # 2-STOP CANDIDATES (if max_stops >= 2 and sufficient race distance)
        # -------------------------------------------------------------
        if max_stops >= 2 and remaining_laps >= 25:
            # Enumerate two pit stops P1, P2
            p1_candidates = [p for p in pit_lap_range if p <= total_laps - 18]
            for p1 in p1_candidates[::2]:  # Sample grid
                for p2 in range(p1 + 10, total_laps - 5, 4):
                    for c2 in ["HARD", "MEDIUM"]:
                        for c3 in ["MEDIUM", "SOFT"]:
                            s1 = StintPlan(current_compound, current_lap, p1, current_tyre_age)
                            s2 = StintPlan(c2, p1 + 1, p2, 0)
                            s3 = StintPlan(c3, p2 + 1, total_laps, 0)

                            # Validate tyre life
                            if (p2 - p1) > self.compound_params.get(c2, {}).get("max_life", 40):
                                continue
                            if (total_laps - p2) > self.compound_params.get(c3, {}).get("max_life", 30):
                                continue

                            candidates.append(
                                CandidateStrategy(
                                    name=f"2-Stop: L{p1} ({c2}) + L{p2} ({c3})",
                                    stints=[s1, s2, s3],
                                    pit_laps=[p1, p2],
                                )
                            )

        return candidates
