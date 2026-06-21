"""Utilidades para calcular ángulos articulares con coordenadas 2D o 3D."""

from __future__ import annotations

import numpy as np


def _convertir_vector(valor, nombre: str) -> np.ndarray:
    """Convierte una entrada a vector NumPy y valida su forma."""
    vector = np.asarray(valor, dtype=float)

    if vector.shape not in {(2,), (3,)}:
        raise ValueError(f"{nombre} debe tener 2 o 3 coordenadas.")

    return vector


def calcular_angulo_vectores(vector_a, vector_b) -> float:
    """Calcula el ángulo en grados entre dos vectores 2D o 3D.

    Acepta listas, tuplas o arreglos NumPy. Si alguno de los vectores tiene
    norma cero, lanza ValueError para evitar divisiones invalidas.
    """
    vector_a_np = _convertir_vector(vector_a, "vector_a")
    vector_b_np = _convertir_vector(vector_b, "vector_b")

    if vector_a_np.shape != vector_b_np.shape:
        raise ValueError("vector_a y vector_b deben tener la misma cantidad de coordenadas.")

    norma_a = np.linalg.norm(vector_a_np)
    norma_b = np.linalg.norm(vector_b_np)

    if np.isclose(norma_a, 0.0):
        raise ValueError("vector_a no puede tener norma cero.")
    if np.isclose(norma_b, 0.0):
        raise ValueError("vector_b no puede tener norma cero.")

    coseno = np.dot(vector_a_np, vector_b_np) / (norma_a * norma_b)
    coseno = np.clip(coseno, -1.0, 1.0)
    angulo = np.degrees(np.arccos(coseno))

    return float(angulo)


def calcular_angulo(punto_a, punto_b, punto_c) -> float:
    """Calcula el ángulo en el punto B formado por los puntos A-B-C.

    Cada punto debe tener coordenadas 2D o 3D en formato lista, tupla o arreglo
    NumPy. Retorna el ángulo en grados como float.
    """
    punto_a_np = _convertir_vector(punto_a, "punto_a")
    punto_b_np = _convertir_vector(punto_b, "punto_b")
    punto_c_np = _convertir_vector(punto_c, "punto_c")

    if punto_a_np.shape != punto_b_np.shape or punto_a_np.shape != punto_c_np.shape:
        raise ValueError("punto_a, punto_b y punto_c deben tener la misma cantidad de coordenadas.")

    vector_ba = punto_a_np - punto_b_np
    vector_bc = punto_c_np - punto_b_np

    return calcular_angulo_vectores(vector_ba, vector_bc)
