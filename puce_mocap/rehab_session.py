"""Sesión acumulada para ejercicios de rehabilitación."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
import time
from typing import Any, Mapping
from uuid import uuid4

from puce_mocap.rehab_analyzer import RehabAnalysisResult
from puce_mocap.rehab_profiles import crear_perfil_demo, movimiento_desde_config
from puce_mocap.movement import RepetitionTracker
from puce_mocap.movement import MovementPhase


@dataclass
class RehabSession:
    """Acumula frames válidos, rango alcanzado y repeticiones estimadas."""

    ejercicio_actual: str
    codigo_paciente: str
    configuracion: Mapping[str, Any] | None = field(default=None, repr=False)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    fuente_datos: str = "mediapipe_live"
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    total_frames: int = 0
    frames_validos: int = 0
    frames_dentro_rango: int = 0
    angulo_maximo_alcanzado: float | None = None
    repeticiones_estimadas: int = 0
    fase_actual: str = MovementPhase.ESPERANDO_INICIO.value
    mensajes_principales: list[str] = field(default_factory=list)
    _inicio_monotonic: float = field(default_factory=time.monotonic, init=False, repr=False)
    _tracker: RepetitionTracker = field(init=False, repr=False)
    _angulo_minimo: float | None = field(default=None, init=False, repr=False)
    _angulo_maximo: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        configuracion = self.configuracion
        if configuracion is None:
            configuracion = crear_perfil_demo()["ejercicios"][self.ejercicio_actual]
        self.configuracion = configuracion
        self._tracker = RepetitionTracker(movimiento_desde_config(configuracion))

    def registrar_resultado(
        self, resultado: RehabAnalysisResult, timestamp: float | None = None
    ) -> RehabAnalysisResult:
        """Registra un frame; las posturas incompletas no cuentan como válidas."""
        if resultado.ejercicio != self.ejercicio_actual:
            raise ValueError(f"El resultado corresponde a {resultado.ejercicio}, no a {self.ejercicio_actual}.")

        self.total_frames += 1
        self._registrar_mensajes(resultado)
        if not resultado.frame_valido or resultado.angulo_actual is None:
            actualizacion = self._tracker.update(
                None, time.monotonic() if timestamp is None else timestamp, valid=False
            )
            self.fase_actual = actualizacion.state.value
            return replace(resultado, fase=actualizacion.phase.value)

        self.frames_validos += 1
        self._angulo_minimo = resultado.angulo_minimo
        self._angulo_maximo = resultado.angulo_maximo
        if resultado.dentro_rango:
            self.frames_dentro_rango += 1

        if self.angulo_maximo_alcanzado is None or resultado.angulo_actual > self.angulo_maximo_alcanzado:
            self.angulo_maximo_alcanzado = float(resultado.angulo_actual)

        actualizacion = self._tracker.update(
            resultado.angulo_actual,
            time.monotonic() if timestamp is None else timestamp,
            valid=True,
            form_ok=resultado.forma_correcta,
        )
        self.repeticiones_estimadas = actualizacion.repetitions
        self.fase_actual = actualizacion.state.value
        return replace(
            resultado,
            fase=actualizacion.phase.value,
            repeticion_completada=actualizacion.repetition_completed,
        )

    def _registrar_mensajes(self, resultado: RehabAnalysisResult) -> None:
        for mensaje in resultado.mensajes:
            if mensaje not in self.mensajes_principales:
                self.mensajes_principales.append(mensaje)

    @property
    def porcentaje_dentro_rango(self) -> float:
        if self.frames_validos == 0:
            return 0.0
        return (self.frames_dentro_rango / self.frames_validos) * 100.0

    @property
    def duracion_segundos(self) -> float:
        return max(0.0, time.monotonic() - self._inicio_monotonic)

    def reiniciar(self) -> None:
        """Reinicia las métricas conservando paciente y ejercicio."""
        self.fecha = datetime.now().isoformat(timespec="seconds")
        self.total_frames = 0
        self.frames_validos = 0
        self.frames_dentro_rango = 0
        self.angulo_maximo_alcanzado = None
        self.repeticiones_estimadas = 0
        self.fase_actual = MovementPhase.ESPERANDO_INICIO.value
        self.mensajes_principales.clear()
        self._inicio_monotonic = time.monotonic()
        self._tracker.reset()
        self._angulo_minimo = None
        self._angulo_maximo = None

    def exportar_resumen(self) -> dict:
        """Exporta la sesión a un diccionario apto para CSV."""
        assert self.configuracion is not None
        inicio = self.configuracion["rango_inicio"]
        objetivo = self.configuracion["rango_objetivo"]
        return {
            "session_id": self.session_id,
            "fuente_datos": self.fuente_datos,
            "fecha": self.fecha,
            "codigo_paciente": self.codigo_paciente,
            "ejercicio": self.ejercicio_actual,
            "total_frames": self.total_frames,
            "frames_validos": self.frames_validos,
            "frames_dentro_rango": self.frames_dentro_rango,
            "porcentaje_dentro_rango": round(self.porcentaje_dentro_rango, 2),
            "angulo_minimo_inicio": inicio["minimo"],
            "angulo_maximo_inicio": inicio["maximo"],
            "angulo_minimo_objetivo": objetivo["minimo"],
            "angulo_maximo_objetivo": objetivo["maximo"],
            "lado": self.configuracion.get("lado", "right"),
            "repeticiones_objetivo": self.configuracion["repeticiones_objetivo"],
            "angulo_maximo_alcanzado": (
                None if self.angulo_maximo_alcanzado is None else round(self.angulo_maximo_alcanzado, 2)
            ),
            "repeticiones_estimadas": self.repeticiones_estimadas,
            "duracion_segundos": round(self.duracion_segundos, 2),
            "observaciones": list(self.mensajes_principales),
        }
