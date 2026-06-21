"""Reglas base para evaluar ejercicios con pesas usando esqueletos 3D."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np

from puce_mocap.angle_utils import calcular_angulo, calcular_angulo_vectores

ESTADO_CORRECTO = "CORRECTO"
ESTADO_CORREGIR = "CORREGIR_POSTURA"
ESTADO_EN_MOVIMIENTO = "EN_MOVIMIENTO"
ESTADO_POSTURA_INCOMPLETA = "POSTURA_INCOMPLETA"
COLOR_VERDE = "verde"
COLOR_ROJO = "rojo"

Punto3D = Sequence[float]
Esqueleto3D = Mapping[str, Punto3D]


@dataclass(frozen=True)
class ExerciseFeedback:
    """Resultado de evaluar un frame de un ejercicio."""

    ejercicio: str
    estado: str
    color: str
    angulos: dict[str, float] = field(default_factory=dict)
    mensajes: list[str] = field(default_factory=list)
    fase: str = "transicion"
    frame_valido: bool = True
    forma_correcta: bool | None = None
    repeticion_completada: bool = False
    angulo_principal: str | None = None

    @property
    def es_correcto(self) -> bool:
        """Indica si el frame evaluado esta dentro de las reglas definidas."""
        if self.forma_correcta is not None:
            return self.forma_correcta
        return self.estado == ESTADO_CORRECTO

    @property
    def form_ok(self) -> bool | None:
        """Alias estable para integraciones que usan nombres en ingles."""
        return self.forma_correcta

    @property
    def repetition_completed(self) -> bool:
        return self.repeticion_completada

    def to_dict(self) -> dict:
        """Exporta el resultado a un diccionario simple."""
        return {
            "ejercicio": self.ejercicio,
            "estado": self.estado,
            "color": self.color,
            "angulos": dict(self.angulos),
            "mensajes": list(self.mensajes),
            "fase": self.fase,
            "frame_valido": self.frame_valido,
            "forma_correcta": self.forma_correcta,
            "repeticion_completada": self.repeticion_completada,
            "angulo_principal": self.angulo_principal,
        }


def _normalizar_lado(lado: str) -> str:
    lado_normalizado = lado.lower().strip()
    if lado_normalizado in {"right", "derecho", "derecha", "d"}:
        return "right"
    if lado_normalizado in {"left", "izquierdo", "izquierda", "i"}:
        return "left"
    raise ValueError("lado debe ser 'right'/'left' o 'derecho'/'izquierdo'.")


def _punto(esqueleto_3d: Esqueleto3D, *nombres: str) -> np.ndarray:
    for nombre in nombres:
        if nombre in esqueleto_3d:
            punto = np.asarray(esqueleto_3d[nombre], dtype=float)
            if punto.shape != (3,):
                raise ValueError(f"{nombre} debe tener exactamente 3 coordenadas [x, y, z].")
            return punto

    opciones = ", ".join(nombres)
    raise ValueError(f"No se encontró ningún punto requerido: {opciones}.")


def _punto_opcional(esqueleto_3d: Esqueleto3D, *nombres: str) -> np.ndarray | None:
    try:
        return _punto(esqueleto_3d, *nombres)
    except ValueError:
        return None


def _nombres_lado(lado: str, articulacion: str) -> tuple[str, ...]:
    mapa = {
        "hip": ("hip", "cadera"),
        "knee": ("knee", "rodilla"),
        "ankle": ("ankle", "tobillo"),
        "foot": ("foot", "foot_index", "toe", "pie", "punta_pie"),
        "shoulder": ("shoulder", "hombro"),
        "elbow": ("elbow", "codo"),
        "wrist": ("wrist", "muneca", "muñeca"),
        "ear": ("ear", "oreja"),
    }
    if articulacion not in mapa:
        raise ValueError(f"Articulación no soportada: {articulacion}.")

    nombres = []
    for base in mapa[articulacion]:
        nombres.extend(
            [
                f"{lado}_{base}",
                f"{base}_{lado}",
            ]
        )
    return tuple(nombres)


def _punto_lado(esqueleto_3d: Esqueleto3D, lado: str, articulacion: str) -> np.ndarray:
    return _punto(esqueleto_3d, *_nombres_lado(lado, articulacion))


def _punto_lado_opcional(esqueleto_3d: Esqueleto3D, lado: str, articulacion: str) -> np.ndarray | None:
    return _punto_opcional(esqueleto_3d, *_nombres_lado(lado, articulacion))


def _centro_bilateral(esqueleto_3d: Esqueleto3D, articulacion: str) -> np.ndarray | None:
    punto_derecho = _punto_lado_opcional(esqueleto_3d, "right", articulacion)
    punto_izquierdo = _punto_lado_opcional(esqueleto_3d, "left", articulacion)
    if punto_derecho is None or punto_izquierdo is None:
        return None
    return (punto_derecho + punto_izquierdo) / 2.0


def _resultado(
    ejercicio: str,
    correcto: bool | None,
    angulos: dict[str, float],
    mensajes: list[str],
    *,
    fase: str,
    angulo_principal: str,
) -> ExerciseFeedback:
    if correcto is None:
        estado = ESTADO_EN_MOVIMIENTO
        color = "amarillo"
    else:
        estado = ESTADO_CORRECTO if correcto else ESTADO_CORREGIR
        color = COLOR_VERDE if correcto else COLOR_ROJO
    return ExerciseFeedback(
        ejercicio=ejercicio,
        estado=estado,
        color=color,
        angulos={nombre: float(valor) for nombre, valor in angulos.items()},
        mensajes=mensajes,
        fase=fase,
        forma_correcta=correcto,
        angulo_principal=angulo_principal,
    )


def _fase_angular(angulo: float, inicio: tuple[float, float], objetivo: tuple[float, float]) -> str:
    if inicio[0] <= angulo <= inicio[1]:
        return "inicio"
    if objetivo[0] <= angulo <= objetivo[1]:
        return "objetivo"
    return "transicion"


def _angulo_tobillo(knee: np.ndarray, ankle: np.ndarray, foot: np.ndarray | None) -> float:
    """Aproxima la flexión de tobillo como desviación respecto a 90 grados."""
    if foot is not None:
        angulo_crudo = calcular_angulo(knee, ankle, foot)
        return abs(90.0 - angulo_crudo)

    vector_pierna = knee - ankle
    vector_vertical = np.array([0.0, 1.0, 0.0])
    return calcular_angulo_vectores(vector_pierna, vector_vertical)


def evaluar_sentadilla(esqueleto_3d: Esqueleto3D) -> ExerciseFeedback:
    """Evalua una sentadilla con reglas iniciales de rodilla, cadera y tobillo."""
    angulos_rodilla: list[float] = []
    angulos_cadera: list[float] = []
    angulos_tobillo: list[float] = []
    for lado in ("right", "left"):
        hip = _punto_lado_opcional(esqueleto_3d, lado, "hip")
        knee = _punto_lado_opcional(esqueleto_3d, lado, "knee")
        ankle = _punto_lado_opcional(esqueleto_3d, lado, "ankle")
        shoulder = _punto_lado_opcional(esqueleto_3d, lado, "shoulder")
        if hip is None or knee is None or ankle is None or shoulder is None:
            continue
        foot = _punto_lado_opcional(esqueleto_3d, lado, "foot")
        angulos_rodilla.append(calcular_angulo(hip, knee, ankle))
        angulos_cadera.append(calcular_angulo(shoulder, hip, knee))
        angulos_tobillo.append(_angulo_tobillo(knee, ankle, foot))
    if not angulos_rodilla:
        raise ValueError("No hay un lado completo para evaluar la sentadilla.")

    angulo_rodilla = float(np.mean(angulos_rodilla))
    angulo_cadera = float(np.mean(angulos_cadera))
    angulo_tobillo = float(max(angulos_tobillo))
    fase = _fase_angular(angulo_rodilla, (160.0, 180.0), (70.0, 100.0))
    correcto: bool | None = None
    mensajes: list[str] = []

    if fase == "objetivo":
        correcto = True
        mensajes.append("Rodilla dentro del rango esperado para el punto bajo de la sentadilla.")
        if angulo_tobillo > 35.0:
            correcto = False
            mensajes.append("Tobillo supera 35 grados; revisa el avance de la rodilla.")
        if angulo_cadera < 45.0:
            correcto = False
            mensajes.append("Cadera menor a 45 grados; revisar postura con el fisioterapeuta.")
    elif fase == "inicio":
        mensajes.append("Posicion inicial confirmada.")
    else:
        mensajes.append("Movimiento en curso; continua hasta el rango objetivo.")

    if correcto is True:
        mensajes.append("Postura correcta en el punto objetivo.")

    return _resultado(
        "Sentadilla",
        correcto,
        {
            "angulo_rodilla": angulo_rodilla,
            "angulo_tobillo": angulo_tobillo,
            "angulo_cadera": angulo_cadera,
        },
        mensajes,
        fase=fase,
        angulo_principal="angulo_rodilla",
    )


def evaluar_press_hombro(esqueleto_3d: Esqueleto3D, lado: str = "right") -> ExerciseFeedback:
    """Evalúa press de hombro por codo inicial o extensión superior."""
    lado = _normalizar_lado(lado)
    shoulder = _punto_lado(esqueleto_3d, lado, "shoulder")
    elbow = _punto_lado(esqueleto_3d, lado, "elbow")
    wrist = _punto_lado(esqueleto_3d, lado, "wrist")
    hip = _punto_lado_opcional(esqueleto_3d, lado, "hip")

    angulo_codo = calcular_angulo(shoulder, elbow, wrist)
    angulos = {"angulo_codo": angulo_codo}
    mensajes: list[str] = []

    codo_inicio_correcto = 80.0 <= angulo_codo <= 100.0
    brazo_extendido = 170.0 <= angulo_codo <= 180.0
    fase = _fase_angular(angulo_codo, (80.0, 100.0), (170.0, 180.0))
    correcto: bool | None = True if fase in {"inicio", "objetivo"} else None

    if codo_inicio_correcto:
        mensajes.append("Codo cercano a 90 grados para la fase inicial del press.")
    if brazo_extendido:
        mensajes.append("Brazo extendido dentro del rango 170-180 grados.")
    if fase == "transicion":
        mensajes.append("Movimiento en curso; continúa entre inicio y extensión.")

    if hip is not None:
        angulos["angulo_hombro"] = calcular_angulo(hip, shoulder, elbow)

    centro_hombros = _centro_bilateral(esqueleto_3d, "shoulder")
    centro_caderas = _centro_bilateral(esqueleto_3d, "hip")
    if centro_hombros is not None and centro_caderas is not None:
        desviacion_tronco = calcular_angulo_vectores(centro_hombros - centro_caderas, np.array([0.0, 1.0, 0.0]))
        angulos["desviacion_tronco"] = desviacion_tronco
        if desviacion_tronco > 20.0:
            correcto = False
            mensajes.append("Posible compensacion corporal; mantener el tronco estable durante el press.")
    else:
        mensajes.append("Compensacion lumbar: validacion futura cuando existan puntos completos del tronco.")

    if correcto is True:
        mensajes.append("Postura correcta.")

    return _resultado(
        "Press de hombro",
        correcto,
        angulos,
        mensajes,
        fase=fase,
        angulo_principal="angulo_codo",
    )


def evaluar_peso_muerto(  # noqa: C901
    esqueleto_3d: Esqueleto3D, vista: str = "lateral"
) -> ExerciseFeedback:
    """Evalua peso muerto con desviacion de tronco y control frontal opcional."""
    hip = _punto_lado(esqueleto_3d, "right", "hip")
    knee = _punto_lado(esqueleto_3d, "right", "knee")
    ankle = _punto_lado(esqueleto_3d, "right", "ankle")
    shoulder = _punto_lado(esqueleto_3d, "right", "shoulder")

    centro_caderas = _centro_bilateral(esqueleto_3d, "hip")
    if centro_caderas is None:
        centro_caderas = hip
    centro_hombros = _centro_bilateral(esqueleto_3d, "shoulder")
    if centro_hombros is None:
        centro_hombros = shoulder

    desviacion_tronco = calcular_angulo_vectores(centro_hombros - centro_caderas, np.array([0.0, 1.0, 0.0]))
    angulo_rodilla = calcular_angulo(hip, knee, ankle)
    angulo_cadera = calcular_angulo(shoulder, hip, knee)

    angulos = {
        "desviacion_tronco": desviacion_tronco,
        "angulo_rodilla": angulo_rodilla,
        "angulo_cadera": angulo_cadera,
    }
    mensajes: list[str] = []
    fase = _fase_angular(angulo_cadera, (160.0, 180.0), (80.0, 130.0))
    correcto: bool | None = True if fase == "objetivo" else None
    mensajes.append(f"Inclinacion del tronco observada: {desviacion_tronco:.1f} grados.")

    ear = _punto_lado_opcional(esqueleto_3d, "right", "ear")
    if ear is not None:
        desviacion_espalda = abs(180.0 - calcular_angulo(ear, shoulder, hip))
        angulos["desviacion_espalda"] = desviacion_espalda
        if fase == "objetivo" and desviacion_espalda > 20.0:
            correcto = False
            mensajes.append("La alineacion oreja-hombro-cadera supera 20 grados; revisar la espalda.")

    left_knee = _punto_lado_opcional(esqueleto_3d, "left", "knee")
    right_knee = _punto_lado_opcional(esqueleto_3d, "right", "knee")
    left_ankle = _punto_lado_opcional(esqueleto_3d, "left", "ankle")
    right_ankle = _punto_lado_opcional(esqueleto_3d, "right", "ankle")
    if vista.lower() == "frontal" and all(
        punto is not None for punto in (left_knee, right_knee, left_ankle, right_ankle)
    ):
        distancia_rodillas = float(np.linalg.norm(right_knee - left_knee))
        distancia_tobillos = float(np.linalg.norm(right_ankle - left_ankle))
        if distancia_tobillos > 0:
            relacion = distancia_rodillas / distancia_tobillos
            angulos["relacion_rodillas_tobillos"] = relacion
            if relacion < 0.75:
                if fase == "objetivo":
                    correcto = False
                mensajes.append("Posible colapso de rodillas hacia adentro; revisar vista frontal.")
            else:
                mensajes.append("Separacion de rodillas consistente con los tobillos.")
    elif vista.lower() != "frontal":
        mensajes.append("La simetria de rodillas requiere una vista frontal adicional.")

    if fase == "inicio":
        mensajes.append("Posicion inicial confirmada.")
    elif fase == "transicion":
        mensajes.append("Movimiento en curso; continúa la flexión de cadera.")
    elif correcto is True:
        mensajes.append("Postura correcta en el punto objetivo.")

    return _resultado(
        "Peso muerto",
        correcto,
        angulos,
        mensajes,
        fase=fase,
        angulo_principal="angulo_cadera",
    )
