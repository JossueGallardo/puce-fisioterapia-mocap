"""Analisis de ejercicios terapeuticos con rangos configurables."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from puce_mocap.angle_utils import calcular_angulo, calcular_angulo_vectores
from puce_mocap.rehab_profiles import EJERCICIOS_REHABILITACION


ESTADO_DENTRO_RANGO = "DENTRO_DEL_RANGO"
ESTADO_FUERA_RANGO = "FUERA_DEL_RANGO"
ESTADO_POSTURA_INCOMPLETA = "POSTURA_INCOMPLETA"

COLOR_VERDE = "verde"
COLOR_AMARILLO = "amarillo"
COLOR_ROJO = "rojo"

MENSAJE_DENTRO_RANGO = "Dentro del rango terapeutico."
MENSAJE_FUERA_RANGO = "Fuera del rango indicado para este perfil."
MENSAJE_POSTURA_INCOMPLETA = "No se detecta postura completa."
MENSAJE_REVISAR = "Revisar con fisioterapeuta."

Punto = Sequence[float]
Esqueleto = Mapping[str, Punto]


@dataclass(frozen=True)
class RehabAnalysisResult:
    """Resultado de evaluar un frame de rehabilitacion."""

    ejercicio: str
    estado: str
    color: str
    angulo_actual: float | None
    angulo_minimo: float
    angulo_maximo: float
    dentro_rango: bool
    mensajes: list[str] = field(default_factory=list)

    @property
    def frame_valido(self) -> bool:
        return self.estado != ESTADO_POSTURA_INCOMPLETA

    def to_dict(self) -> dict[str, Any]:
        return {
            "ejercicio": self.ejercicio,
            "estado": self.estado,
            "color": self.color,
            "angulo_actual": self.angulo_actual,
            "angulo_minimo": self.angulo_minimo,
            "angulo_maximo": self.angulo_maximo,
            "dentro_rango": self.dentro_rango,
            "mensajes": list(self.mensajes),
            "frame_valido": self.frame_valido,
        }


def _normalizar_clave(nombre: str) -> str:
    return nombre.replace("-", "_").replace(" ", "_").lower()


def _normalizar_lado(lado: str) -> str:
    lado_normalizado = lado.lower().strip()
    if lado_normalizado in {"right", "derecho", "derecha", "d"}:
        return "right"
    if lado_normalizado in {"left", "izquierdo", "izquierda", "i"}:
        return "left"
    raise ValueError("El lado debe ser right/left o derecho/izquierdo.")


def _indice(esqueleto: Esqueleto) -> dict[str, tuple[str, Punto]]:
    return {_normalizar_clave(nombre): (nombre, valor) for nombre, valor in esqueleto.items()}


def _convertir_punto(valor: Punto, nombre: str) -> np.ndarray:
    punto = np.asarray(valor, dtype=float)
    if punto.shape not in {(2,), (3,)}:
        raise ValueError(f"{nombre} debe tener 2 o 3 coordenadas.")
    return punto


def _punto(indice: Mapping[str, tuple[str, Punto]], *nombres: str) -> np.ndarray:
    for nombre in nombres:
        clave = _normalizar_clave(nombre)
        if clave in indice:
            nombre_original, valor = indice[clave]
            return _convertir_punto(valor, nombre_original)
    raise ValueError("No se encontro una articulacion requerida.")


def _punto_lado(indice: Mapping[str, tuple[str, Punto]], lado: str, articulacion: str) -> np.ndarray:
    alias = {
        "shoulder": ("shoulder", "hombro"),
        "elbow": ("elbow", "codo"),
        "wrist": ("wrist", "muneca", "muñeca"),
        "index": ("index", "hand", "mano", "dedo_indice"),
        "hip": ("hip", "cadera"),
        "knee": ("knee", "rodilla"),
        "ankle": ("ankle", "tobillo"),
        "foot": ("foot", "foot_index", "toe", "pie", "punta_pie"),
    }
    candidatos: list[str] = []
    for base in alias[articulacion]:
        candidatos.extend((f"{lado}_{base}", f"{base}_{lado}"))
    return _punto(indice, *candidatos)


def _vertical_abajo(punto: np.ndarray) -> np.ndarray:
    if punto.shape == (2,):
        return np.array([0.0, -1.0])
    return np.array([0.0, -1.0, 0.0])


def _calcular_angulo_ejercicio(nombre: str, esqueleto: Esqueleto, lado: str) -> tuple[float, list[str]]:
    indice = _indice(esqueleto)

    if nombre == "flexion_codo":
        hombro = _punto_lado(indice, lado, "shoulder")
        codo = _punto_lado(indice, lado, "elbow")
        muneca = _punto_lado(indice, lado, "wrist")
        return calcular_angulo(hombro, codo, muneca), []

    if nombre == "abduccion_hombro":
        cadera = _punto_lado(indice, lado, "hip")
        hombro = _punto_lado(indice, lado, "shoulder")
        codo = _punto_lado(indice, lado, "elbow")
        return calcular_angulo(cadera, hombro, codo), []

    if nombre == "rotacion_muneca":
        codo = _punto_lado(indice, lado, "elbow")
        muneca = _punto_lado(indice, lado, "wrist")
        indice_mano = _punto_lado(indice, lado, "index")
        return calcular_angulo(codo, muneca, indice_mano), ["Medicion aproximada con puntos visibles de la mano."]

    if nombre == "extension_rodilla":
        cadera = _punto_lado(indice, lado, "hip")
        rodilla = _punto_lado(indice, lado, "knee")
        tobillo = _punto_lado(indice, lado, "ankle")
        return calcular_angulo(cadera, rodilla, tobillo), []

    if nombre == "dorsiflexion_tobillo":
        rodilla = _punto_lado(indice, lado, "knee")
        tobillo = _punto_lado(indice, lado, "ankle")
        pie = _punto_lado(indice, lado, "foot")
        angulo_crudo = calcular_angulo(rodilla, tobillo, pie)
        return abs(90.0 - angulo_crudo), []

    if nombre == "elevacion_pierna_recta":
        cadera = _punto_lado(indice, lado, "hip")
        rodilla = _punto_lado(indice, lado, "knee")
        tobillo = _punto_lado(indice, lado, "ankle")
        elevacion = calcular_angulo_vectores(rodilla - cadera, _vertical_abajo(cadera))
        angulo_rodilla = calcular_angulo(cadera, rodilla, tobillo)
        mensajes = [] if angulo_rodilla >= 160.0 else ["Mantener la rodilla extendida durante la elevacion."]
        return elevacion, mensajes

    raise ValueError(f"Ejercicio de rehabilitacion no soportado: {nombre}.")


def evaluar_ejercicio_rehabilitacion(
    nombre_ejercicio: str,
    esqueleto: Esqueleto,
    perfil: Mapping[str, Any],
) -> RehabAnalysisResult:
    """Evalua un ejercicio usando el rango configurado en el perfil."""
    nombre = _normalizar_clave(nombre_ejercicio)
    if nombre not in EJERCICIOS_REHABILITACION:
        raise ValueError(f"Ejercicio de rehabilitacion no soportado: {nombre_ejercicio}.")

    ejercicios = perfil.get("ejercicios")
    if not isinstance(ejercicios, Mapping) or nombre not in ejercicios:
        raise ValueError(f"El perfil no tiene configurado el ejercicio {nombre}.")

    configuracion = ejercicios[nombre]
    minimo = float(configuracion["angulo_minimo"])
    maximo = float(configuracion["angulo_maximo"])
    lado = _normalizar_lado(str(configuracion.get("lado", "right")))

    try:
        angulo_actual, mensajes_adicionales = _calcular_angulo_ejercicio(nombre, esqueleto, lado)
    except (KeyError, ValueError):
        return RehabAnalysisResult(
            ejercicio=nombre,
            estado=ESTADO_POSTURA_INCOMPLETA,
            color=COLOR_ROJO,
            angulo_actual=None,
            angulo_minimo=minimo,
            angulo_maximo=maximo,
            dentro_rango=False,
            mensajes=[MENSAJE_POSTURA_INCOMPLETA],
        )

    dentro_rango = minimo <= angulo_actual <= maximo
    if nombre == "elevacion_pierna_recta" and mensajes_adicionales:
        dentro_rango = False

    if dentro_rango:
        estado = ESTADO_DENTRO_RANGO
        color = COLOR_VERDE
        mensajes = [MENSAJE_DENTRO_RANGO]
    else:
        estado = ESTADO_FUERA_RANGO
        color = COLOR_AMARILLO
        mensajes = [MENSAJE_FUERA_RANGO, MENSAJE_REVISAR]

    mensajes.extend(mensajes_adicionales)
    return RehabAnalysisResult(
        ejercicio=nombre,
        estado=estado,
        color=color,
        angulo_actual=float(angulo_actual),
        angulo_minimo=minimo,
        angulo_maximo=maximo,
        dentro_rango=dentro_rango,
        mensajes=mensajes,
    )
