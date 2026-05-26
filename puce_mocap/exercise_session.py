"""Sesion simple para contar frames correctos y repeticiones."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from puce_mocap.exercise_rules import ESTADO_CORRECTO, ExerciseFeedback


@dataclass
class ExerciseSession:
    """Acumula resultados de un ejercicio durante una sesion simulada o real."""

    ejercicio: str
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    total_frames: int = 0
    frames_correctos: int = 0
    repeticiones: int = 0
    mensajes_principales: list[str] = field(default_factory=list)
    _frame_anterior_correcto: bool | None = field(default=None, init=False, repr=False)

    def registrar_feedback(self, feedback: ExerciseFeedback) -> None:
        """Registra un frame evaluado y actualiza metricas de sesion."""
        if feedback.ejercicio != self.ejercicio:
            raise ValueError(f"El feedback corresponde a {feedback.ejercicio}, no a {self.ejercicio}.")

        frame_correcto = feedback.estado == ESTADO_CORRECTO
        self.total_frames += 1
        if frame_correcto:
            self.frames_correctos += 1

        if self._frame_anterior_correcto is False and frame_correcto:
            self.repeticiones += 1
        self._frame_anterior_correcto = frame_correcto

        for mensaje in feedback.mensajes:
            if mensaje not in self.mensajes_principales:
                self.mensajes_principales.append(mensaje)

    def agregar_frame(self, feedback: ExerciseFeedback) -> None:
        """Alias legible para registrar un frame evaluado."""
        self.registrar_feedback(feedback)

    @property
    def porcentaje_correcto(self) -> float:
        """Calcula el porcentaje de frames correctos de la sesion."""
        if self.total_frames == 0:
            return 0.0
        return (self.frames_correctos / self.total_frames) * 100.0

    def exportar_resumen(self) -> dict:
        """Exporta la sesion a un diccionario simple para reportes CSV."""
        return {
            "fecha": self.fecha,
            "ejercicio": self.ejercicio,
            "total_frames": self.total_frames,
            "frames_correctos": self.frames_correctos,
            "porcentaje_correcto": round(self.porcentaje_correcto, 2),
            "repeticiones": self.repeticiones,
            "mensajes_principales": list(self.mensajes_principales),
        }

