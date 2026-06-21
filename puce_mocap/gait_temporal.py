"""Metricas temporales de marcha basadas en ciclos, no en un solo frame."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class GaitCycle:
    side: str
    timestamp: float
    peak_flexion_angle: float
    range_of_motion: float
    step_length: float | None


@dataclass(frozen=True)
class GaitTemporalMetrics:
    right_angle: float | None
    left_angle: float | None
    asymmetry: float | None
    step_length: float | None
    completed_cycles: int
    length_unit: str


class _KneeCycleDetector:
    def __init__(self, side: str, min_interval: float, min_excursion: float):
        self.side = side
        self.min_interval = min_interval
        self.min_excursion = min_excursion
        self.samples: deque[tuple[float, float]] = deque(maxlen=3)
        self.max_since_cycle: float | None = None
        self.last_cycle_at: float | None = None

    def update(self, angle: float, timestamp: float, step_length: float | None) -> GaitCycle | None:
        self.max_since_cycle = angle if self.max_since_cycle is None else max(self.max_since_cycle, angle)
        self.samples.append((timestamp, angle))
        if len(self.samples) < 3:
            return None
        (_, before), (middle_time, middle), (_, after) = self.samples
        is_minimum = middle < before and middle <= after
        excursion = (self.max_since_cycle or middle) - middle
        interval_ok = self.last_cycle_at is None or middle_time - self.last_cycle_at >= self.min_interval
        if not is_minimum or excursion < self.min_excursion or not interval_ok:
            return None
        self.last_cycle_at = middle_time
        self.max_since_cycle = after
        return GaitCycle(self.side, middle_time, middle, excursion, step_length)


class GaitCycleAnalyzer:
    def __init__(self, alpha: float = 0.35, min_interval: float = 0.4, min_excursion: float = 10.0):
        self.alpha = alpha
        self.detectors = {
            "right": _KneeCycleDetector("right", min_interval, min_excursion),
            "left": _KneeCycleDetector("left", min_interval, min_excursion),
        }
        self.filtered = {"right": None, "left": None}
        self.cycles: dict[str, deque[GaitCycle]] = {
            "right": deque(maxlen=20),
            "left": deque(maxlen=20),
        }
        self._last_step_side: str | None = None
        self._max_separation = 0.0
        self._step_lengths: deque[float] = deque(maxlen=20)

    def reset(self) -> None:
        self.__init__(self.alpha, self.detectors["right"].min_interval, self.detectors["right"].min_excursion)

    def update(
        self,
        right_angle: float,
        left_angle: float,
        ankle_separation_ap: float | None,
        timestamp: float,
        *,
        view: str = "lateral",
        length_unit: str = "sin_especificar",
    ) -> GaitTemporalMetrics:
        for side, angle in (("right", right_angle), ("left", left_angle)):
            previous = self.filtered[side]
            self.filtered[side] = angle if previous is None else self.alpha * angle + (1 - self.alpha) * previous
        if ankle_separation_ap is not None:
            self._max_separation = max(self._max_separation, abs(float(ankle_separation_ap)))

        if view.lower() == "lateral":
            for side in ("right", "left"):
                cycle = self.detectors[side].update(
                    float(self.filtered[side]), timestamp, self._max_separation or None
                )
                if cycle is not None:
                    self.cycles[side].append(cycle)
                    if self._last_step_side is not None and self._last_step_side != side and cycle.step_length is not None:
                        self._step_lengths.append(cycle.step_length)
                        self._max_separation = 0.0
                    self._last_step_side = side

        asymmetry = None
        if len(self.cycles["right"]) >= 2 and len(self.cycles["left"]) >= 2:
            right_peak = fmean(cycle.peak_flexion_angle for cycle in self.cycles["right"])
            left_peak = fmean(cycle.peak_flexion_angle for cycle in self.cycles["left"])
            asymmetry = abs(right_peak - left_peak)
        step_length = fmean(self._step_lengths) if len(self._step_lengths) >= 2 else None
        return GaitTemporalMetrics(
            right_angle=float(self.filtered["right"]),
            left_angle=float(self.filtered["left"]),
            asymmetry=asymmetry,
            step_length=step_length,
            completed_cycles=len(self.cycles["right"]) + len(self.cycles["left"]),
            length_unit=length_unit,
        )
