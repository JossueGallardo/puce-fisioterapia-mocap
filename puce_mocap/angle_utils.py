"""Utilidades para calcular angulos articulares con coordenadas 3D."""

from __future__ import annotations

import numpy as np


def _convertir_vector_3d(valor, nombre: str) -> np.ndarray:
    """Convierte una entrada a vector NumPy 3D y valida su forma."""
    vector = np.asarray(valor, dtype=float)

    if vector.shape != (3,):
        raise ValueError(f"{nombre} debe tener exactamente 3 coordenadas [x, y, z].")

    return vector


def calcular_angulo_vectores(vector_a, vector_b) -> float:
    """Calcula el angulo en grados entre dos vectores 3D.

    Acepta listas, tuplas o arreglos NumPy. Si alguno de los vectores tiene
    norma cero, lanza ValueError para evitar divisiones invalidas.
    """
    vector_a_np = _convertir_vector_3d(vector_a, "vector_a")
    vector_b_np = _convertir_vector_3d(vector_b, "vector_b")

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
    """Calcula el angulo en el punto B formado por los puntos A-B-C.

    Cada punto debe tener coordenadas 3D en formato lista, tupla o arreglo
    NumPy: [x, y, z]. Retorna el angulo en grados como float.
    """
    punto_a_np = _convertir_vector_3d(punto_a, "punto_a")
    punto_b_np = _convertir_vector_3d(punto_b, "punto_b")
    punto_c_np = _convertir_vector_3d(punto_c, "punto_c")

    vector_ba = punto_a_np - punto_b_np
    vector_bc = punto_c_np - punto_b_np

    return calcular_angulo_vectores(vector_ba, vector_bc)

