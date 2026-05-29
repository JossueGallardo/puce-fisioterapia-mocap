"""Adaptador inicial para conectar datos de FreeMoCap con reglas PUCE.

Esta capa no asume rutas internas ni formatos cerrados de FreeMoCap. Su
responsabilidad es recibir diccionarios de articulaciones 3D ya cargados,
normalizar nombres comunes y entregar el resultado a las reglas del modulo de
ejercicios con pesas.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from puce_mocap.exercise_rules import (
    ExerciseFeedback,
    evaluar_peso_muerto,
    evaluar_press_hombro,
    evaluar_sentadilla,
)


_ALIASES_ARTICULACIONES = {
    "head": ("head", "Head", "nose", "Nose", "NOSE", "face", "Face"),
    "right_shoulder": ("right_shoulder", "rightShoulder", "RShoulder", "r_shoulder", "right shoulder"),
    "left_shoulder": ("left_shoulder", "leftShoulder", "LShoulder", "l_shoulder", "left shoulder"),
    "right_elbow": ("right_elbow", "rightElbow", "RElbow", "r_elbow", "right elbow"),
    "left_elbow": ("left_elbow", "leftElbow", "LElbow", "l_elbow", "left elbow"),
    "right_wrist": ("right_wrist", "rightWrist", "RWrist", "r_wrist", "right wrist"),
    "left_wrist": ("left_wrist", "leftWrist", "LWrist", "l_wrist", "left wrist"),
    "right_hip": ("right_hip", "rightHip", "RHip", "r_hip", "right hip"),
    "left_hip": ("left_hip", "leftHip", "LHip", "l_hip", "left hip"),
    "right_knee": ("right_knee", "rightKnee", "RKnee", "r_knee", "right knee"),
    "left_knee": ("left_knee", "leftKnee", "LKnee", "l_knee", "left knee"),
    "right_ankle": ("right_ankle", "rightAnkle", "RAnkle", "r_ankle", "right ankle"),
    "left_ankle": ("left_ankle", "leftAnkle", "LAnkle", "l_ankle", "left ankle"),
    "right_foot": ("right_foot", "rightFoot", "right_foot_index", "rightToe", "RFoot", "right foot"),
    "left_foot": ("left_foot", "leftFoot", "left_foot_index", "leftToe", "LFoot", "left foot"),
}


_ALIASES_MARCHA = {
    "head": ("head", "Head", "nose", "Nose", "NOSE"),
    "nose": ("nose", "Nose", "NOSE", "head", "Head"),
    "right_shoulder": ("right_shoulder", "rightShoulder", "RShoulder", "r_shoulder", "right shoulder"),
    "left_shoulder": ("left_shoulder", "leftShoulder", "LShoulder", "l_shoulder", "left shoulder"),
    "right_hip": ("right_hip", "rightHip", "RHip", "r_hip", "right hip"),
    "left_hip": ("left_hip", "leftHip", "LHip", "l_hip", "left hip"),
    "right_knee": ("right_knee", "rightKnee", "RKnee", "r_knee", "right knee"),
    "left_knee": ("left_knee", "leftKnee", "LKnee", "l_knee", "left knee"),
    "right_ankle": ("right_ankle", "rightAnkle", "RAnkle", "r_ankle", "right ankle"),
    "left_ankle": ("left_ankle", "leftAnkle", "LAnkle", "l_ankle", "left ankle"),
    "right_foot_index": (
        "right_foot_index",
        "rightFootIndex",
        "right_foot",
        "rightFoot",
        "rightToe",
        "RFoot",
        "right foot",
    ),
    "left_foot_index": (
        "left_foot_index",
        "leftFootIndex",
        "left_foot",
        "leftFoot",
        "leftToe",
        "LFoot",
        "left foot",
    ),
}


def _normalizar_clave(clave: str) -> str:
    return clave.replace("-", "_").replace(" ", "_").lower()


def _convertir_punto_3d(valor: Sequence[float], nombre: str) -> list[float]:
    punto = np.asarray(valor, dtype=float)
    if punto.shape != (3,):
        raise ValueError(f"{nombre} debe tener exactamente 3 coordenadas [x, y, z].")
    return punto.astype(float).tolist()


def normalizar_articulaciones_freemocap(articulaciones_3d: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    """Normaliza nombres de articulaciones 3D al formato usado por PUCE.

    El parametro debe ser un diccionario ya cargado desde una fuente externa,
    por ejemplo datos exportados por FreeMoCap o una conversion intermedia.
    La funcion no lee archivos ni depende de rutas internas de FreeMoCap.
    """
    indice_entrada = {_normalizar_clave(nombre): (nombre, valor) for nombre, valor in articulaciones_3d.items()}
    normalizado: dict[str, list[float]] = {}

    for nombre_puce, alias in _ALIASES_ARTICULACIONES.items():
        for candidato in alias:
            clave = _normalizar_clave(candidato)
            if clave in indice_entrada:
                nombre_original, valor = indice_entrada[clave]
                normalizado[nombre_puce] = _convertir_punto_3d(valor, nombre_original)
                break

    return normalizado


def normalizar_esqueleto_marcha_freemocap(articulaciones_3d: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    """Normaliza articulaciones 3D para el analizador de marcha.

    Esta funcion no lee archivos ni asume rutas internas de FreeMoCap. Recibe un
    diccionario ya cargado desde una exportacion o conversion intermedia y deja
    los nombres listos para `puce_mocap.gait_analyzer.analizar_marcha`.
    """
    indice_entrada = {_normalizar_clave(nombre): (nombre, valor) for nombre, valor in articulaciones_3d.items()}
    normalizado: dict[str, list[float]] = {}

    for nombre_puce, alias in _ALIASES_MARCHA.items():
        for candidato in alias:
            clave = _normalizar_clave(candidato)
            if clave in indice_entrada:
                nombre_original, valor = indice_entrada[clave]
                normalizado[nombre_puce] = _convertir_punto_3d(valor, nombre_original)
                break

    return normalizado


def evaluar_ejercicio_freemocap(
    articulaciones_3d: Mapping[str, Sequence[float]],
    ejercicio: str,
    lado: str = "right",
) -> ExerciseFeedback:
    """Evalua un ejercicio usando datos 3D con nombres estilo FreeMoCap.

    Esta funcion prepara la integracion futura con sesiones reales de FreeMoCap:
    primero normaliza nombres de articulaciones y despues llama a las reglas
    institucionales del modulo de pesas.
    """
    esqueleto = normalizar_articulaciones_freemocap(articulaciones_3d)
    ejercicio_normalizado = ejercicio.lower().strip()

    if ejercicio_normalizado in {"sentadilla", "squat"}:
        return evaluar_sentadilla(esqueleto)
    if ejercicio_normalizado in {"press_hombro", "press de hombro", "shoulder_press", "shoulder press"}:
        return evaluar_press_hombro(esqueleto, lado=lado)
    if ejercicio_normalizado in {"peso_muerto", "peso muerto", "deadlift"}:
        return evaluar_peso_muerto(esqueleto)

    raise ValueError("Ejercicio no soportado. Usa sentadilla, press_hombro o peso_muerto.")
