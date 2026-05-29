import pytest

from puce_mocap.gait_analyzer import ESTADO_ATENCION, ESTADO_NORMAL, ESTADO_REVISAR, analizar_marcha


def esqueleto_marcha_normal():
    return {
        "nose": [0.0, 2.4, 0.0],
        "left_shoulder": [-0.2, 2.0, 0.0],
        "right_shoulder": [0.2, 2.0, 0.0],
        "left_hip": [-0.2, 1.0, 0.0],
        "right_hip": [0.2, 1.0, 0.0],
        "left_knee": [-0.2, 0.5, 0.0],
        "right_knee": [0.2, 0.5, 0.0],
        "left_ankle": [-0.2, 0.0, 0.0],
        "right_ankle": [0.2, 0.0, 0.0],
    }


def esqueleto_con_asimetria():
    esqueleto = esqueleto_marcha_normal()
    esqueleto["left_ankle"] = [0.05, 0.067, 0.0]
    return esqueleto


def esqueleto_con_tronco_inclinado():
    esqueleto = esqueleto_marcha_normal()
    esqueleto["left_shoulder"] = [0.3, 2.0, 0.0]
    esqueleto["right_shoulder"] = [0.7, 2.0, 0.0]
    return esqueleto


def test_analizar_marcha_calcula_metricas_basicas_normales():
    resultado = analizar_marcha(esqueleto_marcha_normal())

    assert resultado.estado == ESTADO_NORMAL
    assert resultado.color == "verde"
    assert resultado.frame_valido
    assert resultado.metricas["inclinacion_tronco"] == pytest.approx(0.0)
    assert resultado.metricas["angulo_rodilla_derecha"] == pytest.approx(180.0)
    assert resultado.metricas["angulo_rodilla_izquierda"] == pytest.approx(180.0)
    assert resultado.metricas["asimetria_rodillas"] == pytest.approx(0.0)
    assert resultado.metricas["longitud_paso"] == pytest.approx(0.4)


def test_analizar_marcha_marca_amarillo_por_asimetria_moderada():
    resultado = analizar_marcha(esqueleto_con_asimetria())

    assert resultado.estado == ESTADO_ATENCION
    assert resultado.color == "amarillo"
    assert resultado.metricas["asimetria_rodillas"] > 10.0
    assert any("Asimetria" in mensaje for mensaje in resultado.mensajes)


def test_analizar_marcha_marca_rojo_por_inclinacion_alta():
    resultado = analizar_marcha(esqueleto_con_tronco_inclinado())

    assert resultado.estado == ESTADO_REVISAR
    assert resultado.color == "rojo"
    assert resultado.metricas["inclinacion_tronco"] > 15.0
    assert any("fisioterapeuta" in mensaje for mensaje in resultado.mensajes)


def test_analizar_marcha_con_datos_incompletos_no_rompe():
    resultado = analizar_marcha({"right_hip": [0.0, 1.0, 0.0]})

    assert resultado.estado == ESTADO_REVISAR
    assert resultado.color == "rojo"
    assert not resultado.frame_valido
    assert resultado.metricas["longitud_paso"] is None
