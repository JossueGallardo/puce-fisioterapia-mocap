import numpy as np
import pytest

from puce_mocap.angle_utils import calcular_angulo, calcular_angulo_vectores


def test_calcular_angulo_90_grados():
    angulo = calcular_angulo([1, 0, 0], [0, 0, 0], [0, 1, 0])

    assert angulo == pytest.approx(90.0)


def test_calcular_angulo_180_grados():
    angulo = calcular_angulo([-1, 0, 0], [0, 0, 0], [1, 0, 0])

    assert angulo == pytest.approx(180.0)


def test_calcular_angulo_0_grados():
    angulo = calcular_angulo([1, 0, 0], [0, 0, 0], [2, 0, 0])

    assert angulo == pytest.approx(0.0)


def test_calcular_angulo_45_grados_aproximado():
    angulo = calcular_angulo([1, 0, 0], [0, 0, 0], [1, 1, 0])

    assert angulo == pytest.approx(45.0)


def test_calcular_angulo_con_listas_de_python():
    cadera = [0.0, 1.0, 0.0]
    rodilla = [0.0, 0.0, 0.0]
    tobillo = [1.0, 0.0, 0.0]

    angulo = calcular_angulo(cadera, rodilla, tobillo)

    assert isinstance(angulo, float)
    assert angulo == pytest.approx(90.0)


def test_calcular_angulo_vectores_acepta_numpy_arrays():
    vector_a = np.array([1.0, 0.0, 0.0])
    vector_b = np.array([0.0, 1.0, 0.0])

    assert calcular_angulo_vectores(vector_a, vector_b) == pytest.approx(90.0)


def test_calcular_angulo_vectores_error_con_vector_cero():
    with pytest.raises(ValueError, match="norma cero"):
        calcular_angulo_vectores([0, 0, 0], [1, 0, 0])


def test_calcular_angulo_error_con_punto_invalido():
    with pytest.raises(ValueError, match="3 coordenadas"):
        calcular_angulo([1, 0], [0, 0, 0], [1, 0, 0])
