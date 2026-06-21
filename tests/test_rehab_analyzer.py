import pytest

from puce_mocap.rehab_analyzer import (
    ESTADO_DENTRO_RANGO,
    ESTADO_FUERA_RANGO,
    ESTADO_POSTURA_INCOMPLETA,
    WristRotationCalibrator,
    evaluar_ejercicio_rehabilitacion,
)
from puce_mocap.rehab_profiles import crear_perfil_demo


def esqueleto_codo_90():
    return {
        "right_shoulder": [1.0, 0.0, 0.0],
        "right_elbow": [0.0, 0.0, 0.0],
        "right_wrist": [0.0, 1.0, 0.0],
    }


def esqueleto_codo_180():
    return {
        "right_shoulder": [-1.0, 0.0, 0.0],
        "right_elbow": [0.0, 0.0, 0.0],
        "right_wrist": [1.0, 0.0, 0.0],
    }


def test_flexion_codo_dentro_del_rango():
    resultado = evaluar_ejercicio_rehabilitacion("flexion_codo", esqueleto_codo_90(), crear_perfil_demo())

    assert resultado.estado == ESTADO_DENTRO_RANGO
    assert resultado.color == "verde"
    assert resultado.angulo_actual == pytest.approx(90.0)
    assert resultado.dentro_rango


def test_flexion_codo_fuera_del_rango():
    resultado = evaluar_ejercicio_rehabilitacion("flexion_codo", esqueleto_codo_180(), crear_perfil_demo())

    assert resultado.estado == ESTADO_FUERA_RANGO
    assert resultado.color == "amarillo"
    assert resultado.angulo_actual == pytest.approx(180.0)
    assert not resultado.dentro_rango


def test_postura_incompleta_no_es_frame_valido():
    resultado = evaluar_ejercicio_rehabilitacion("flexion_codo", {}, crear_perfil_demo())

    assert resultado.estado == ESTADO_POSTURA_INCOMPLETA
    assert resultado.color == "rojo"
    assert resultado.angulo_actual is None
    assert not resultado.frame_valido
    assert resultado.mensajes == ["No se detecta postura completa."]


def test_rotacion_muneca_requiere_calibracion_y_mide_relativo():
    perfil = crear_perfil_demo()
    neutro = {
        "right_elbow": [0.0, 0.0, 0.0],
        "right_wrist": [1.0, 0.0, 0.0],
        "right_index": [1.0, 1.0, 0.0],
        "right_pinky": [1.0, 1.0, 0.0],
    }
    rotado = dict(neutro)
    rotado.update({"right_index": [1.0, 0.0, 1.0], "right_pinky": [1.0, 0.0, 1.0]})

    sin_calibrar = evaluar_ejercicio_rehabilitacion("rotacion_muneca", rotado, perfil)
    assert not sin_calibrar.frame_valido

    calibrador = WristRotationCalibrator()
    calibrador.calibrar(neutro)
    resultado = evaluar_ejercicio_rehabilitacion("rotacion_muneca", rotado, perfil, calibrador)

    assert resultado.angulo_actual == pytest.approx(90.0)
    assert resultado.dentro_rango
