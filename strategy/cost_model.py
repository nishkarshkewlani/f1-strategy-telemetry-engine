"""Strategy cost model with explicit incremental pit loss accounting."""

from dataclasses import dataclass, field
import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# Default circuit-calibrated pace parameters (Monza / Silverstone reference)
DEFAULT_COMPOUND_PARAMS: Dict[str, Dict[str, float]] = {
    "SOFT": {"base_offset": -0.6, "degradation_per_lap": 0.085, "max_life": 25},
    "MEDIUM": {"base_offset": 0.0, "degradation_per_lap": 0.050, "max_life": 38},
    "HARD": {"base_offset": 0.5, "degradation_per_lap": 0.025, "max_life": 52},
    "INTERMEDIATE": {"base_offset": 4.5, "degradation_per_lap": 0.060, "max_life": 40},
    "WET": {"base_offset": 8.0, "degradation_per_lap": 0.040, "max_life": 40},
}

# Standard incremental pit loss (seconds lost relative to staying on green-flag track)
DEFAULT_INCREMENTAL_PIT_LOSS = 20.5  # Typical European GP pit loss (total lane time ~24s minus track time ~4s)
SAFETY_CAR_PIT_LOSS = 11.0         # Under SC, cars on track go slow (~60%), so pitting costs far less


@dataclass
class StintPlan:
    """Definition of a single stint in a candidate strategy."""
    compound: str
    lap_start: int
    lap_end: int
    starting_tyre_age: int = 0

    @property
    def lap_count(self) -> int:
        return self.lap_end - self.lap_start + 1


@dataclass
class CandidateStrategy:
    """A complete remaining-race strategy candidate."""
    name: str
    stints: List[StintPlan]
    pit_laps: List[int] = field(default_factory=list)
    total_remaining_time: float = 0.0
    delta_to_best: float = 0.0
    stint_breakdown: List[Dict[str, float]] = field(default_factory=list)
    assumptions: Dict[str, float] = field(default_factory=dict)
    rationale: str = ""


class StrategyCostModel:
    """Evaluates the time cost of a race strategy without double-counting pit loss."""

    def __init__(
        self,
        base_lap_time: float = 85.0,
        incremental_pit_loss: float = DEFAULT_INCREMENTAL_PIT_LOSS,
        sc_pit_loss: float = SAFETY_CAR_PIT_LOSS,
        compound_params: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        self.base_lap_time = base_lap_time
        self.incremental_pit_loss = incremental_pit_loss
        self.sc_pit_loss = sc_pit_loss
        self.compound_params = compound_params or DEFAULT_COMPOUND_PARAMS

    def estimate_lap_time(
        self,
        compound: str,
        tyre_age: int,
        lap_number: int,
        is_sc: bool = False,
        fuel_correction_per_lap: float = -0.035,  # Car gets lighter (~0.035s per lap)
    ) -> float:
        """Estimate single lap duration."""
        if is_sc:
            return self.base_lap_time * 1.35  # Delta pace under safety car

        params = self.compound_params.get(compound.upper(), self.compound_params["MEDIUM"])
        compound_offset = params["base_offset"]
        degradation = params["degradation_per_lap"] * tyre_age
        fuel_effect = fuel_correction_per_lap * lap_number

        return self.base_lap_time + compound_offset + degradation + fuel_effect

    def evaluate_strategy(
        self,
        strategy: CandidateStrategy,
        current_lap: int,
        total_laps: int,
        sc_window: Optional[List[int]] = None,
        weather_rain_lap: Optional[int] = None,
    ) -> CandidateStrategy:
        """Compute exact cumulative time for remaining race laps under explicit scenario rules."""
        sc_laps = set(sc_window or [])
        total_time = 0.0
        breakdown = []

        for stint in strategy.stints:
            stint_time = 0.0
            tyre_age = stint.starting_tyre_age

            for lap in range(stint.lap_start, stint.lap_end + 1):
                if lap <= current_lap:
                    continue  # Only evaluate remaining laps

                is_sc = lap in sc_laps

                # Weather penalty if slicks on wet track or vice versa
                weather_penalty = 0.0
                if weather_rain_lap and lap >= weather_rain_lap:
                    if stint.compound in ["SOFT", "MEDIUM", "HARD"]:
                        weather_penalty = 15.0  # Massive pace loss for slicks in wet
                elif weather_rain_lap and lap < weather_rain_lap:
                    if stint.compound in ["INTERMEDIATE", "WET"]:
                        weather_penalty = 8.0   # Intermediates overheating on dry track

                lap_est = self.estimate_lap_time(stint.compound, tyre_age, lap, is_sc=is_sc) + weather_penalty
                stint_time += lap_est
                tyre_age += 1

            total_time += stint_time
            breakdown.append({
                "compound": stint.compound,
                "laps": stint.lap_count,
                "time_sec": round(stint_time, 2),
            })

        # Add pit loss for each pit stop occurring in remaining race
        pit_time_total = 0.0
        for pit_lap in strategy.pit_laps:
            if pit_lap > current_lap:
                # If pitting during Safety Car window, use reduced pit loss
                loss = self.sc_pit_loss if pit_lap in sc_laps else self.incremental_pit_loss
                pit_time_total += loss

        total_time += pit_time_total

        strategy.total_remaining_time = round(total_time, 3)
        strategy.stint_breakdown = breakdown
        strategy.assumptions = {
            "base_lap_time": self.base_lap_time,
            "incremental_pit_loss": self.incremental_pit_loss,
            "sc_pit_loss": self.sc_pit_loss,
            "pit_loss_total": round(pit_time_total, 2),
            "safety_car_laps": list(sc_laps),
        }
        return strategy
