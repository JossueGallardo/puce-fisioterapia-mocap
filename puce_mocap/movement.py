"""Motor temporal reutilizable para reconocer ciclos completos de movimiento."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class MovementPhase(str, Enum):
    CALIBRANDO_INICIO = "calibrando_inicio"
    ESPERANDO_INICIO = "esperando_inicio"
    BUSCANDO_OBJETIVO = "buscando_objetivo"
    REGRESANDO_INICIO = "regresando_inicio"
    INICIO = "inicio"
    OBJETIVO = "objetivo"
    TRANSICION = "transicion"
    NO_DETECTADO = "no_detectado"


@dataclass(frozen=True)
class AngleRange:
    minimo: float
    maximo: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.minimo) or not math.isfinite(self.maximo):
            raise ValueError("Los límites angulares deben ser finitos.")
        if self.minimo > self.maximo:
            raise ValueError("El límite mínimo no puede superar el máximo.")

    def contiene(self, valor: float, margen: float = 0.0) -> bool:
        return self.minimo - margen <= valor <= self.maximo + margen

    def se_solapa(self, otro: "AngleRange", margen: float = 0.0) -> bool:
        return max(self.minimo, otro.minimo) <= min(self.maximo, otro.maximo) + margen


@dataclass(frozen=True)
class MovementDefinition:
    start_range: AngleRange
    target_range: AngleRange
    hysteresis_deg: float = 3.0
    dwell_seconds: float = 0.2
    min_cycle_seconds: float = 0.6
    invalid_reset_seconds: float = 1.0
    ema_alpha: float = 0.35

    def __post_init__(self) -> None:
        if self.start_range.se_solapa(self.target_range):
            raise ValueError("Los rangos de inicio y objetivo no pueden solaparse.")
        if self.hysteresis_deg < 0:
            raise ValueError("La histéresis no puede ser negativa.")
        if self.dwell_seconds < 0 or self.min_cycle_seconds < 0 or self.invalid_reset_seconds <= 0:
            raise ValueError("Los tiempos del movimiento no son válidos.")
        if not 0.0 < self.ema_alpha <= 1.0:
            raise ValueError("ema_alpha debe estar en el intervalo (0, 1].")


@dataclass(frozen=True)
class MovementUpdate:
    phase: MovementPhase
    state: MovementPhase
    filtered_angle: float | None
    repetitions: int
    repetition_completed: bool = False


class RepetitionTracker:
    """Reconoce inicio -> objetivo -> inicio y descarta oscilaciones breves."""

    def __init__(self, definition: MovementDefinition):
        self.definition = definition
        self.state = MovementPhase.ESPERANDO_INICIO
        self.repetitions = 0
        self._filtered_angle: float | None = None
        self._candidate: MovementPhase | None = None
        self._candidate_since: float | None = None
        self._cycle_started_at: float | None = None
        self._last_valid_at: float | None = None

    @property
    def filtered_angle(self) -> float | None:
        return self._filtered_angle

    def arm_from_start(self, angle: float, timestamp: float) -> MovementUpdate:
        """Arma el ciclo tras una calibración inicial estable ya confirmada."""
        angle = float(angle)
        if not math.isfinite(angle) or not self.definition.start_range.contiene(
            angle, self.definition.hysteresis_deg
        ):
            raise ValueError("El ángulo calibrado no pertenece al rango inicial activo.")
        self._filtered_angle = angle
        self._last_valid_at = float(timestamp)
        self._cycle_started_at = float(timestamp)
        self._clear_candidate()
        self.state = MovementPhase.BUSCANDO_OBJETIVO
        return self._result(MovementPhase.INICIO)

    def reset(self, keep_repetitions: bool = False) -> None:
        self.state = MovementPhase.ESPERANDO_INICIO
        if not keep_repetitions:
            self.repetitions = 0
        self._filtered_angle = None
        self._candidate = None
        self._candidate_since = None
        self._cycle_started_at = None
        self._last_valid_at = None

    def update(  # noqa: C901
        self,
        angle: float | None,
        timestamp: float,
        valid: bool = True,
        form_ok: bool | None = None,
    ) -> MovementUpdate:
        if not valid or angle is None or not math.isfinite(float(angle)):
            if self._last_valid_at is not None and timestamp - self._last_valid_at >= self.definition.invalid_reset_seconds:
                repetitions = self.repetitions
                self.reset(keep_repetitions=True)
                self.repetitions = repetitions
            self._clear_candidate()
            return self._result(MovementPhase.NO_DETECTADO)

        self._last_valid_at = timestamp
        angle = float(angle)
        if self._filtered_angle is None:
            self._filtered_angle = angle
        else:
            alpha = self.definition.ema_alpha
            self._filtered_angle = alpha * angle + (1.0 - alpha) * self._filtered_angle

        phase = self._classify(self._filtered_angle)
        raw_phase = self._classify_raw(angle)
        eligible = form_ok is not False
        completed = False

        if self.state == MovementPhase.ESPERANDO_INICIO:
            # La postura inicial también requiere permanencia. Esto evita armar
            # un ciclo con una estimación aislada cuando la persona entra o sale
            # del encuadre.
            if eligible and self._confirmed(MovementPhase.INICIO, phase, timestamp):
                self.state = MovementPhase.BUSCANDO_OBJETIVO
                self._cycle_started_at = timestamp
        elif self.state == MovementPhase.BUSCANDO_OBJETIVO:
            if eligible and self._confirmed(MovementPhase.OBJETIVO, phase, timestamp):
                self.state = MovementPhase.REGRESANDO_INICIO
        elif self.state == MovementPhase.REGRESANDO_INICIO:
            # El retorno usa el ángulo crudo para no arrastrar el EMA, pero debe
            # permanecer en el rango inicial antes de cerrar el ciclo.
            if eligible and self._confirmed(MovementPhase.INICIO, raw_phase, timestamp):
                cycle_time = timestamp - (self._cycle_started_at if self._cycle_started_at is not None else timestamp)
                if cycle_time >= self.definition.min_cycle_seconds:
                    self.repetitions += 1
                    completed = True
                    self.state = MovementPhase.BUSCANDO_OBJETIVO
                    self._cycle_started_at = timestamp

        return self._result(phase, completed)

    def _classify(self, angle: float) -> MovementPhase:
        margin = self.definition.hysteresis_deg
        if self.definition.start_range.contiene(angle, margin if self._candidate == MovementPhase.INICIO else 0.0):
            return MovementPhase.INICIO
        if self.definition.target_range.contiene(angle, margin if self._candidate == MovementPhase.OBJETIVO else 0.0):
            return MovementPhase.OBJETIVO
        return MovementPhase.TRANSICION

    def _classify_raw(self, angle: float) -> MovementPhase:
        margin = self.definition.hysteresis_deg
        if self.definition.start_range.contiene(angle, margin):
            return MovementPhase.INICIO
        if self.definition.target_range.contiene(angle, margin):
            return MovementPhase.OBJETIVO
        return MovementPhase.TRANSICION

    def _confirmed(self, expected: MovementPhase, phase: MovementPhase, timestamp: float) -> bool:
        if phase != expected:
            self._clear_candidate()
            return False
        if self._candidate != expected:
            self._candidate = expected
            self._candidate_since = timestamp
            return self.definition.dwell_seconds == 0.0
        assert self._candidate_since is not None
        if timestamp - self._candidate_since + 1e-9 >= self.definition.dwell_seconds:
            self._clear_candidate()
            return True
        return False

    def _clear_candidate(self) -> None:
        self._candidate = None
        self._candidate_since = None

    def _result(self, phase: MovementPhase, completed: bool = False) -> MovementUpdate:
        return MovementUpdate(
            phase=phase,
            state=self.state,
            filtered_angle=self._filtered_angle,
            repetitions=self.repetitions,
            repetition_completed=completed,
        )
