"""Sesión de análisis de marcha para Semana 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
import time
from uuid import uuid4

from puce_mocap.gait_analyzer import ESTADO_ATENCION, ESTADO_NORMAL, ESTADO_REVISAR, GaitAnalysisResult


@dataclass
class _OnlineStats:
    count: int = 0
    total: float = 0.0

    def add(self, value: float | None) -> None:
        if value is None or not math.isfinite(float(value)):
            return
        self.count += 1
        self.total += float(value)

    @property
    def mean(self) -> float | None:
        return None if self.count == 0 else self.total / self.count


def _redondear(valor: float | None, decimales: int = 2) -> float | None:
    if valor is None:
        return None
    return round(valor, decimales)


@dataclass
class GaitSession:
    """Acumula resultados de una sesión de caminadora."""

    session_id: str = field(default_factory=lambda: uuid4().hex)
    fuente_datos: str = "mediapipe_live"
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    inicio_monotonic: float = field(default_factory=time.monotonic)
    total_frames: int = 0
    frames_validos: int = 0
    alertas_verdes: int = 0
    alertas_amarillas: int = 0
    alertas_rojas: int = 0
    mensajes_principales: list[str] = field(default_factory=list)
    _inclinaciones: _OnlineStats = field(default_factory=_OnlineStats, init=False, repr=False)
    _asimetrias: _OnlineStats = field(default_factory=_OnlineStats, init=False, repr=False)
    _longitudes_paso: _OnlineStats = field(default_factory=_OnlineStats, init=False, repr=False)

    def registrar_resultado(self, resultado: GaitAnalysisResult) -> None:
        """Registra un fotograma analizado y actualiza métricas acumuladas."""
        self.total_frames += 1
        if not resultado.frame_valido:
            self._registrar_mensajes(resultado)
            return

        self.frames_validos += 1
        if resultado.estado == ESTADO_NORMAL:
            self.alertas_verdes += 1
        elif resultado.estado == ESTADO_ATENCION:
            self.alertas_amarillas += 1
        elif resultado.estado == ESTADO_REVISAR:
            self.alertas_rojas += 1

        metricas = resultado.metricas
        self._agregar_metrica(self._inclinaciones, metricas.get("inclinacion_tronco"))
        self._agregar_metrica(self._asimetrias, metricas.get("asimetria_rodillas"))
        self._agregar_metrica(self._longitudes_paso, metricas.get("longitud_paso"))
        self._registrar_mensajes(resultado)

    def _registrar_mensajes(self, resultado: GaitAnalysisResult) -> None:
        for mensaje in resultado.mensajes:
            if mensaje not in self.mensajes_principales:
                self.mensajes_principales.append(mensaje)

    @staticmethod
    def _agregar_metrica(destino: _OnlineStats, valor: float | str | None) -> None:
        if isinstance(valor, (int, float)):
            destino.add(float(valor))

    @property
    def duracion_segundos(self) -> float:
        """Duración transcurrida desde el inicio de sesión."""
        return max(0.0, time.monotonic() - self.inicio_monotonic)

    @property
    def porcentaje_verde(self) -> float:
        return self._porcentaje(self.alertas_verdes)

    @property
    def porcentaje_amarillo(self) -> float:
        return self._porcentaje(self.alertas_amarillas)

    @property
    def porcentaje_rojo(self) -> float:
        return self._porcentaje(self.alertas_rojas)

    def _porcentaje(self, cantidad: int) -> float:
        if self.frames_validos == 0:
            return 0.0
        return (cantidad / self.frames_validos) * 100.0

    @property
    def estado_global(self) -> str:
        """Resume la sesión sin emitir diagnósticos clínicos."""
        if self.frames_validos == 0:
            return "SIN_DATOS_VALIDOS"
        if self.porcentaje_rojo >= 20.0:
            return ESTADO_REVISAR
        if self.porcentaje_rojo >= 5.0 or self.porcentaje_amarillo + self.porcentaje_rojo >= 20.0:
            return ESTADO_ATENCION
        return ESTADO_NORMAL

    def exportar_resumen(self, duracion_segundos: float | None = None) -> dict:
        """Exporta la sesión a un diccionario para reportes CSV."""
        duracion = self.duracion_segundos if duracion_segundos is None else duracion_segundos
        return {
            "session_id": self.session_id,
            "fuente_datos": self.fuente_datos,
            "fecha": self.fecha,
            "duracion_segundos": round(duracion, 2),
            "total_frames": self.total_frames,
            "frames_validos": self.frames_validos,
            "porcentaje_verde": round(self.porcentaje_verde, 2),
            "porcentaje_amarillo": round(self.porcentaje_amarillo, 2),
            "porcentaje_rojo": round(self.porcentaje_rojo, 2),
            "promedio_inclinacion_tronco": _redondear(self._inclinaciones.mean),
            "promedio_asimetria_rodillas": _redondear(self._asimetrias.mean),
            "promedio_longitud_paso": _redondear(self._longitudes_paso.mean),
            "estado_global": self.estado_global,
            "observaciones": list(self.mensajes_principales),
        }
