"""Sesion acumulada para ejercicios de rehabilitacion."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import time

from puce_mocap.rehab_analyzer import RehabAnalysisResult


@dataclass
class RehabSession:
    """Acumula frames validos, rango alcanzado y repeticiones estimadas."""

    ejercicio_actual: str
    codigo_paciente: str
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    total_frames: int = 0
    frames_validos: int = 0
    frames_dentro_rango: int = 0
    angulo_maximo_alcanzado: float | None = None
    repeticiones_estimadas: int = 0
    mensajes_principales: list[str] = field(default_factory=list)
    _inicio_monotonic: float = field(default_factory=time.monotonic, init=False, repr=False)
    _anterior_dentro: bool | None = field(default=None, init=False, repr=False)
    _angulo_minimo: float | None = field(default=None, init=False, repr=False)
    _angulo_maximo: float | None = field(default=None, init=False, repr=False)

    def registrar_resultado(self, resultado: RehabAnalysisResult) -> None:
        """Registra un frame; las posturas incompletas no cuentan como validas."""
        if resultado.ejercicio != self.ejercicio_actual:
            raise ValueError(f"El resultado corresponde a {resultado.ejercicio}, no a {self.ejercicio_actual}.")

        self.total_frames += 1
        self._registrar_mensajes(resultado)
        if not resultado.frame_valido or resultado.angulo_actual is None:
            return

        self.frames_validos += 1
        self._angulo_minimo = resultado.angulo_minimo
        self._angulo_maximo = resultado.angulo_maximo
        if resultado.dentro_rango:
            self.frames_dentro_rango += 1

        if self.angulo_maximo_alcanzado is None or resultado.angulo_actual > self.angulo_maximo_alcanzado:
            self.angulo_maximo_alcanzado = float(resultado.angulo_actual)

        if self._anterior_dentro is False and resultado.dentro_rango:
            self.repeticiones_estimadas += 1
        self._anterior_dentro = resultado.dentro_rango

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
        """Reinicia las metricas conservando paciente y ejercicio."""
        self.fecha = datetime.now().isoformat(timespec="seconds")
        self.total_frames = 0
        self.frames_validos = 0
        self.frames_dentro_rango = 0
        self.angulo_maximo_alcanzado = None
        self.repeticiones_estimadas = 0
        self.mensajes_principales.clear()
        self._inicio_monotonic = time.monotonic()
        self._anterior_dentro = None
        self._angulo_minimo = None
        self._angulo_maximo = None

    def exportar_resumen(self) -> dict:
        """Exporta la sesion a un diccionario apto para CSV."""
        return {
            "fecha": self.fecha,
            "codigo_paciente": self.codigo_paciente,
            "ejercicio": self.ejercicio_actual,
            "total_frames": self.total_frames,
            "frames_validos": self.frames_validos,
            "frames_dentro_rango": self.frames_dentro_rango,
            "porcentaje_dentro_rango": round(self.porcentaje_dentro_rango, 2),
            "angulo_minimo_objetivo": self._angulo_minimo,
            "angulo_maximo_objetivo": self._angulo_maximo,
            "angulo_maximo_alcanzado": (
                None if self.angulo_maximo_alcanzado is None else round(self.angulo_maximo_alcanzado, 2)
            ),
            "repeticiones_estimadas": self.repeticiones_estimadas,
            "duracion_segundos": round(self.duracion_segundos, 2),
            "observaciones": list(self.mensajes_principales),
        }
