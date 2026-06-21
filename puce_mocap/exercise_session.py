"""Sesión de ejercicios con conteo temporal de ciclos completos."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
import time
from uuid import uuid4

from puce_mocap.exercise_rules import ESTADO_CORRECTO, ExerciseFeedback
from puce_mocap.movement import AngleRange, MovementDefinition, MovementPhase, RepetitionTracker


DEFINICIONES_MOVIMIENTO = {
    "Sentadilla": ("angulo_rodilla", MovementDefinition(AngleRange(160, 180), AngleRange(70, 100))),
    "Press de hombro": ("angulo_codo", MovementDefinition(AngleRange(80, 100), AngleRange(170, 180))),
    "Peso muerto": ("angulo_cadera", MovementDefinition(AngleRange(160, 180), AngleRange(80, 130))),
}


@dataclass
class ExerciseSession:
    """Acumula resultados de un ejercicio durante una sesión simulada o real."""

    ejercicio: str
    session_id: str = field(default_factory=lambda: uuid4().hex)
    fuente_datos: str = "mediapipe_live"
    definicion: MovementDefinition | None = field(default=None, repr=False)
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    total_frames: int = 0
    frames_evaluables_forma: int = 0
    frames_correctos: int = 0
    repeticiones: int = 0
    mensajes_principales: list[str] = field(default_factory=list)
    fase_actual: str = MovementPhase.ESPERANDO_INICIO.value
    _tracker: RepetitionTracker = field(init=False, repr=False)
    _angulo_principal: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            self._angulo_principal, definition_default = DEFINICIONES_MOVIMIENTO[self.ejercicio]
        except KeyError as exc:
            raise ValueError(f"Ejercicio no soportado para conteo: {self.ejercicio}.") from exc
        self.definicion = self.definicion or definition_default
        self._tracker = RepetitionTracker(self.definicion)

    def registrar_feedback(self, feedback: ExerciseFeedback, timestamp: float | None = None) -> ExerciseFeedback:
        """Registra un frame evaluado y actualiza métricas de sesión."""
        if feedback.ejercicio != self.ejercicio:
            raise ValueError(f"El feedback corresponde a {feedback.ejercicio}, no a {self.ejercicio}.")

        self.total_frames += 1
        forma_correcta = feedback.forma_correcta
        if forma_correcta is None and feedback.angulo_principal is None:
            forma_correcta = feedback.estado == ESTADO_CORRECTO
        if feedback.frame_valido and forma_correcta is not None:
            self.frames_evaluables_forma += 1
            if forma_correcta:
                self.frames_correctos += 1

        nombre_angulo = feedback.angulo_principal or self._angulo_principal
        actualizacion = self._tracker.update(
            feedback.angulos.get(nombre_angulo),
            time.monotonic() if timestamp is None else float(timestamp),
            valid=feedback.frame_valido and nombre_angulo in feedback.angulos,
            form_ok=forma_correcta,
        )
        self.repeticiones = actualizacion.repetitions
        self.fase_actual = actualizacion.state.value

        for mensaje in feedback.mensajes:
            if mensaje not in self.mensajes_principales:
                self.mensajes_principales.append(mensaje)

        return replace(
            feedback,
            fase=actualizacion.phase.value,
            repeticion_completada=actualizacion.repetition_completed,
        )

    def agregar_frame(self, feedback: ExerciseFeedback, timestamp: float | None = None) -> ExerciseFeedback:
        """Alias legible para registrar un frame evaluado."""
        return self.registrar_feedback(feedback, timestamp=timestamp)

    @property
    def porcentaje_correcto(self) -> float:
        """Calcula el porcentaje de fotogramas correctos de la sesión."""
        if self.frames_evaluables_forma == 0:
            return 0.0
        return (self.frames_correctos / self.frames_evaluables_forma) * 100.0

    def reiniciar(self) -> None:
        self.fecha = datetime.now().isoformat(timespec="seconds")
        self.total_frames = 0
        self.frames_evaluables_forma = 0
        self.frames_correctos = 0
        self.repeticiones = 0
        self.mensajes_principales.clear()
        self.fase_actual = MovementPhase.ESPERANDO_INICIO.value
        self._tracker.reset()

    def configurar_movimiento(self, definicion: MovementDefinition) -> None:
        """Aplica rangos clínicos nuevos y reinicia solo este ejercicio."""
        self.definicion = definicion
        self._tracker = RepetitionTracker(definicion)
        self.reiniciar()

    def exportar_resumen(self) -> dict:
        """Exporta la sesión a un diccionario simple para reportes CSV."""
        assert self.definicion is not None
        return {
            "session_id": self.session_id,
            "fuente_datos": self.fuente_datos,
            "fecha": self.fecha,
            "ejercicio": self.ejercicio,
            "total_frames": self.total_frames,
            "frames_evaluables_forma": self.frames_evaluables_forma,
            "frames_correctos": self.frames_correctos,
            "porcentaje_correcto": round(self.porcentaje_correcto, 2),
            "repeticiones": self.repeticiones,
            "fase_actual": self.fase_actual,
            "angulo_minimo_inicio": self.definicion.start_range.minimo,
            "angulo_maximo_inicio": self.definicion.start_range.maximo,
            "angulo_minimo_objetivo": self.definicion.target_range.minimo,
            "angulo_maximo_objetivo": self.definicion.target_range.maximo,
            "mensajes_principales": list(self.mensajes_principales),
        }
