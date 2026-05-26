from puce_mocap.freemocap_adapter import evaluar_ejercicio_freemocap, normalizar_articulaciones_freemocap


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
