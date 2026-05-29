from puce_mocap.freemocap_adapter import (
    evaluar_ejercicio_freemocap,
    normalizar_articulaciones_freemocap,
    normalizar_esqueleto_marcha_freemocap,
)


def datos_freemocap_simulados():
    return {
        "rightShoulder": [0.0, 2.0, 0.0],
        "rightHip": [0.0, 1.0, 0.0],
        "rightKnee": [0.0, 0.0, 0.0],
        "rightAnkle": [1.0, 0.0, 0.0],
        "right_foot_index": [1.0, 1.0, 0.0],
    }


def test_normalizar_articulaciones_freemocap_convierte_alias():
    normalizado = normalizar_articulaciones_freemocap(datos_freemocap_simulados())

    assert normalizado["right_shoulder"] == [0.0, 2.0, 0.0]
    assert normalizado["right_hip"] == [0.0, 1.0, 0.0]
    assert normalizado["right_knee"] == [0.0, 0.0, 0.0]
    assert normalizado["right_ankle"] == [1.0, 0.0, 0.0]
    assert normalizado["right_foot"] == [1.0, 1.0, 0.0]


def test_adaptador_alimenta_reglas_de_sentadilla():
    feedback = evaluar_ejercicio_freemocap(datos_freemocap_simulados(), "sentadilla")

    assert feedback.ejercicio == "Sentadilla"
    assert feedback.estado == "CORRECTO"
    assert feedback.angulos["angulo_rodilla"] == 90.0


def test_normalizar_esqueleto_marcha_freemocap_prepara_alias_de_caminadora():
    datos = {
        "Nose": [0.0, 2.4, 0.0],
        "rightShoulder": [0.2, 2.0, 0.0],
        "leftShoulder": [-0.2, 2.0, 0.0],
        "rightHip": [0.2, 1.0, 0.0],
        "leftHip": [-0.2, 1.0, 0.0],
        "rightKnee": [0.2, 0.5, 0.0],
        "leftKnee": [-0.2, 0.5, 0.0],
        "rightAnkle": [0.2, 0.0, 0.0],
        "leftAnkle": [-0.2, 0.0, 0.0],
        "rightFootIndex": [0.25, -0.1, 0.0],
    }

    normalizado = normalizar_esqueleto_marcha_freemocap(datos)

    assert normalizado["nose"] == [0.0, 2.4, 0.0]
    assert normalizado["right_shoulder"] == [0.2, 2.0, 0.0]
    assert normalizado["left_ankle"] == [-0.2, 0.0, 0.0]
    assert normalizado["right_foot_index"] == [0.25, -0.1, 0.0]
