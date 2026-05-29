"""Analisis inicial de marcha para el Modulo 3 / Semana 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

import numpy as np

from puce_mocap.angle_utils import calcular_angulo, calcular_angulo_vectores

ESTADO_NORMAL = "NORMAL"
ESTADO_ATENCION = "ATENCION"
ESTADO_REVISAR = "REVISAR_CON_FISIOTERAPEUTA"

COLOR_VERDE = "verde"
COLOR_AMARILLO = "amarillo"
COLOR_ROJO = "rojo"

MENSAJE_POSTURA_INCOMPLETA = "Alejate de la camara hasta que se vean cabeza, cadera, rodillas, tobillos y pies."

Punto = Sequence[float]
Esqueleto = Mapping[str, Punto]


@dataclass(frozen=True)
class GaitAnalysisResult:
    """Resultado de analizar un frame de marcha."""

    estado: str
    color: str
    metricas: dict[str, float | None] = field(default_factory=dict)
    mensajes: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    frame_valido: bool = True

    def to_dict(self) -> dict:
        """Exporta el resultado a un diccionario simple."""
        return {
            "estado": self.estado,
            "color": self.color,
            "metricas": dict(self.metricas),
            "mensajes": list(self.mensajes),
            "timestamp": self.timestamp,
            "frame_valido": self.frame_valido,
        }


def _normalizar_clave(nombre: str) -> str:
    return nombre.replace("-", "_").replace(" ", "_").lower()


def _convertir_punto(valor: Punto, nombre: str) -> np.ndarray:
    punto = np.asarray(valor, dtype=float)
    if punto.shape not in {(2,), (3,)}:
        raise ValueError(f"{nombre} debe tener 2 o 3 coordenadas.")
    return punto


def _indice_esqueleto(esqueleto: Esqueleto) -> dict[str, tuple[str, Punto]]:
    return {_normalizar_clave(nombre): (nombre, valor) for nombre, valor in esqueleto.items()}


def _punto(indice: Mapping[str, tuple[str, Punto]], *nombres: str) -> np.ndarray:
    for nombre in nombres:
        clave = _normalizar_clave(nombre)
        if clave in indice:
            nombre_original, valor = indice[clave]
            return _convertir_punto(valor, nombre_original)
    opciones = ", ".join(nombres)
    raise ValueError(f"No se encontro ningun punto requerido: {opciones}.")


def _punto_opcional(indice: Mapping[str, tuple[str, Punto]], *nombres: str) -> np.ndarray | None:
    try:
        return _punto(indice, *nombres)
    except ValueError:
        return None


def _centro(punto_a: np.ndarray, punto_b: np.ndarray) -> np.ndarray:
    if punto_a.shape != punto_b.shape:
        raise ValueError("Los puntos bilaterales deben tener la misma dimension.")
    return (punto_a + punto_b) / 2.0


def _vertical_para(punto: np.ndarray) -> np.ndarray:
    if punto.shape == (2,):
        return np.array([0.0, 1.0])
    return np.array([0.0, 1.0, 0.0])


def _desviacion_vertical(vector: np.ndarray) -> float:
    angulo = calcular_angulo_vectores(vector, _vertical_para(vector))
    return float(min(angulo, abs(180.0 - angulo)))


def _distancia(punto_a: np.ndarray, punto_b: np.ndarray) -> float:
    if punto_a.shape != punto_b.shape:
        raise ValueError("Los puntos deben tener la misma dimension para calcular distancia.")
    return float(np.linalg.norm(punto_a - punto_b))


def _resultado_incompleto(mensajes: list[str] | None = None) -> GaitAnalysisResult:
    mensajes_resultado = [MENSAJE_POSTURA_INCOMPLETA]
    if mensajes:
        mensajes_resultado.extend(mensajes)
    return GaitAnalysisResult(
        estado=ESTADO_REVISAR,
        color=COLOR_ROJO,
        metricas={
            "inclinacion_tronco": None,
            "angulo_rodilla_derecha": None,
            "angulo_rodilla_izquierda": None,
            "asimetria_rodillas": None,
            "longitud_paso": None,
            "oscilacion_lateral_cadera": None,
        },
        mensajes=mensajes_resultado,
        frame_valido=False,
    )


def analizar_marcha(esqueleto_3d: Esqueleto) -> GaitAnalysisResult:
    """Recibe coordenadas 2D/3D de articulaciones y retorna metricas de marcha.

    Esta funcion no emite diagnosticos medicos. Sus etiquetas solo orientan la
    revision tecnica y la supervision de un fisioterapeuta.
    """
    indice = _indice_esqueleto(esqueleto_3d)

    try:
        left_shoulder = _punto(indice, "left_shoulder", "leftShoulder")
        right_shoulder = _punto(indice, "right_shoulder", "rightShoulder")
        left_hip = _punto(indice, "left_hip", "leftHip")
        right_hip = _punto(indice, "right_hip", "rightHip")
        left_knee = _punto(indice, "left_knee", "leftKnee")
        right_knee = _punto(indice, "right_knee", "rightKnee")
        left_ankle = _punto(indice, "left_ankle", "leftAnkle")
        right_ankle = _punto(indice, "right_ankle", "rightAnkle")
    except ValueError as exc:
        return _resultado_incompleto([str(exc)])

    try:
        centro_hombros = _centro(left_shoulder, right_shoulder)
        centro_caderas = _centro(left_hip, right_hip)
        inclinacion_tronco = _desviacion_vertical(centro_hombros - centro_caderas)
        angulo_rodilla_derecha = calcular_angulo(right_hip, right_knee, right_ankle)
        angulo_rodilla_izquierda = calcular_angulo(left_hip, left_knee, left_ankle)
        asimetria_rodillas = abs(angulo_rodilla_derecha - angulo_rodilla_izquierda)
        longitud_paso = _distancia(left_ankle, right_ankle)
        oscilacion_lateral_cadera = float(abs(left_hip[0] - right_hip[0]))
    except ValueError as exc:
        return _resultado_incompleto([str(exc)])

    metricas = {
        "inclinacion_tronco": float(inclinacion_tronco),
        "angulo_rodilla_derecha": float(angulo_rodilla_derecha),
        "angulo_rodilla_izquierda": float(angulo_rodilla_izquierda),
        "asimetria_rodillas": float(asimetria_rodillas),
        "longitud_paso": float(longitud_paso),
        "oscilacion_lateral_cadera": float(oscilacion_lateral_cadera),
    }

    severidad = 0
    mensajes: list[str] = []

    if inclinacion_tronco <= 5.0:
        mensajes.append("Inclinacion del tronco dentro del rango basico observado.")
    elif inclinacion_tronco <= 15.0:
        severidad = max(severidad, 1)
        mensajes.append("Inclinacion del tronco requiere atencion; mantener postura erguida.")
    else:
        severidad = max(severidad, 2)
        mensajes.append("Inclinacion del tronco elevada; revisar con fisioterapeuta.")

    if asimetria_rodillas <= 10.0:
        mensajes.append("Simetria de rodillas dentro del rango basico observado.")
    else:
        severidad = max(severidad, 1)
        mensajes.append("Asimetria entre rodillas mayor a 10 grados; observar la marcha.")

    mensajes.append("Longitud de paso calculada entre tobillos.")

    if severidad == 0:
        estado = ESTADO_NORMAL
        color = COLOR_VERDE
        mensajes.append("VERDE / NORMAL: marcha dentro de rangos basicos observados.")
    elif severidad == 1:
        estado = ESTADO_ATENCION
        color = COLOR_AMARILLO
        mensajes.append("AMARILLO / ATENCION: revisar la tecnica durante la sesion.")
    else:
        estado = ESTADO_REVISAR
        color = COLOR_ROJO
        mensajes.append("ROJO / REVISAR_CON_FISIOTERAPEUTA: sugerir revision profesional.")

    return GaitAnalysisResult(estado=estado, color=color, metricas=metricas, mensajes=mensajes)
