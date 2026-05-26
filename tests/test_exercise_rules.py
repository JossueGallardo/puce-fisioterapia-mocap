import pytest

from puce_mocap.exercise_rules import (
    ESTADO_CORRECTO,
    ESTADO_CORREGIR,
    evaluar_peso_muerto,
    evaluar_press_hombro,
    evaluar_sentadilla,
)


def sentadilla_correcta():
    return {
        "right_shoulder": [0.0, 2.0, 0.0],
        "right_hip": [0.0, 1.0, 0.0],
        "right_knee": [0.0, 0.0, 0.0],
        "right_ankle": [1.0, 0.0, 0.0],
        "right_foot": [1.0, 1.0, 0.0],
    }


def sentadilla_incorrecta_por_rodilla():
    return {
        "right_shoulder": [-1.0, 1.0, 0.0],
        "right_hip": [-1.0, 0.0, 0.0],
        "right_knee": [0.0, 0.0, 0.0],
        "right_ankle": [1.0, 0.0, 0.0],
        "right_foot": [1.0, 1.0, 0.0],
    }


def press_hombro_extendido():
    return {
        "right_shoulder": [0.0, 0.0, 0.0],
        "right_elbow": [0.0, 1.0, 0.0],
        "right_wrist": [0.0, 2.0, 0.0],
    }


def peso_muerto_tronco_correcto():
    return {
        "right_shoulder": [0.2, 1.0, 0.0],
        "left_shoulder": [-0.2, 1.0, 0.0],
        "right_hip": [0.2, 0.0, 0.0],
        "left_hip": [-0.2, 0.0, 0.0],
        "right_knee": [0.2, -0.8, 0.0],
        "left_knee": [-0.2, -0.8, 0.0],
        "right_ankle": [0.2, -1.6, 0.0],
        "left_ankle": [-0.2, -1.6, 0.0],
    }


def test_sentadilla_correcta_con_rodilla_entre_70_y_100_grados():
    feedback = evaluar_sentadilla(sentadilla_correcta())

    assert feedback.estado == ESTADO_CORRECTO
    assert feedback.color == "verde"
    assert feedback.angulos["angulo_rodilla"] == pytest.approx(90.0)


def test_sentadilla_incorrecta_por_rodilla_fuera_de_rango():
    feedback = evaluar_sentadilla(sentadilla_incorrecta_por_rodilla())

    assert feedback.estado == ESTADO_CORREGIR
    assert feedback.color == "rojo"
    assert feedback.angulos["angulo_rodilla"] == pytest.approx(180.0)
    assert any("Rodilla fuera" in mensaje for mensaje in feedback.mensajes)


def test_press_hombro_en_extension_correcta():
    feedback = evaluar_press_hombro(press_hombro_extendido())

    assert feedback.estado == ESTADO_CORRECTO
    assert feedback.angulos["angulo_codo"] == pytest.approx(180.0)
    assert any("Brazo extendido" in mensaje for mensaje in feedback.mensajes)


def test_peso_muerto_con_tronco_dentro_de_rango():
    feedback = evaluar_peso_muerto(peso_muerto_tronco_correcto())

    assert feedback.estado == ESTADO_CORRECTO
    assert feedback.angulos["desviacion_tronco"] == pytest.approx(0.0)
    assert any("Tronco dentro" in mensaje for mensaje in feedback.mensajes)

