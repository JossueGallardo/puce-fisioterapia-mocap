"""Sesion de analisis de marcha para Semana 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import math
import time

from puce_mocap.gait_analyzer import ESTADO_ATENCION, ESTADO_NORMAL, ESTADO_REVISAR, GaitAnalysisResult


def _promedio(valores: list[float]) -> float | None:
    valores_validos = [valor for valor in valores if not math.isnan(valor)]
    if not valores_validos:
        return None
    return sum(valores_validos) / len(valores_validos)


def _redondear(valor: float | None, decimales: int = 2) -> float | None:
    if valor is None:
        return None
    return round(valor, decimales)


@dataclass
class GaitSession:
    """Acumula resultados de una sesion de caminadora."""

    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    inicio_monotonic: float = field(default_factory=time.monotonic)
    total_frames: int = 0
    frames_validos: int = 0
    alertas_verdes: int = 0
    alertas_amarillas: int = 0
    alertas_rojas: int = 0
    mensajes_principales: list[str] = field(default_factory=list)
    _inclinaciones: list[float] = field(default_factory=list, init=False, repr=False)
    _asimetrias: list[float] = field(default_factory=list, init=False, repr=False)
    _longitudes_paso: list[float] = field(default_factory=list, init=False, repr=False)

    def registrar_resultado(self, resultado: GaitAnalysisResult) -> None:
        """Registra un frame analizado y actualiza metricas acumuladas."""
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
    def _agregar_metrica(destino: list[float], valor: float | None) -> None:
        if valor is not None:
            destino.append(float(valor))

    @property
    def duracion_segundos(self) -> float:
        """Duracion transcurrida desde el inicio de sesion."""
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
        """Resume la sesion sin emitir diagnosticos clinicos."""
        if self.frames_validos == 0:
            return "SIN_DATOS_VALIDOS"
        if self.alertas_rojas > 0:
            return ESTADO_REVISAR
        if self.alertas_amarillas > 0:
            return ESTADO_ATENCION
        return ESTADO_NORMAL

    def exportar_resumen(self, duracion_segundos: float | None = None) -> dict:
        """Exporta la sesion a un diccionario para reportes CSV."""
        duracion = self.duracion_segundos if duracion_segundos is None else duracion_segundos
        return {
            "fecha": self.fecha,
            "duracion_segundos": round(duracion, 2),
            "total_frames": self.total_frames,
            "frames_validos": self.frames_validos,
            "porcentaje_verde": round(self.porcentaje_verde, 2),
            "porcentaje_amarillo": round(self.porcentaje_amarillo, 2),
            "porcentaje_rojo": round(self.porcentaje_rojo, 2),
            "promedio_inclinacion_tronco": _redondear(_promedio(self._inclinaciones)),
            "promedio_asimetria_rodillas": _redondear(_promedio(self._asimetrias)),
            "promedio_longitud_paso": _redondear(_promedio(self._longitudes_paso)),
            "estado_global": self.estado_global,
            "observaciones": list(self.mensajes_principales),
        }
