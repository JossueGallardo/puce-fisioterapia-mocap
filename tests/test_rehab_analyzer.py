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


def esqueleto_codos_bilaterales():
    return {
        "right_shoulder": [-1.0, 0.0, 0.0],
        "right_elbow": [0.0, 0.0, 0.0],
        "right_wrist": [1.0, 0.0, 0.0],
        "left_shoulder": [1.0, 0.0, 0.0],
        "left_elbow": [0.0, 0.0, 0.0],
        "left_wrist": [0.0, 1.0, 0.0],
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
    assert resultado.mensajes == [
        "Mantenga visibles hombro, codo y muñeca de al menos una extremidad. Puede realizarse sentado."
    ]


@pytest.mark.parametrize(
    ("ejercicio", "esqueleto"),
    [
        (
            "flexion_codo",
            {
                "right_shoulder": [1.0, 0.0, 0.0],
                "right_elbow": [0.0, 0.0, 0.0],
                "right_wrist": [0.0, 1.0, 0.0],
            },
        ),
        (
            "abduccion_hombro",
            {
                "right_hip": [0.0, -1.0, 0.0],
                "right_shoulder": [0.0, 0.0, 0.0],
                "right_elbow": [1.0, 0.0, 0.0],
            },
        ),
        (
            "extension_rodilla",
            {
                "right_hip": [-1.0, 0.0, 0.0],
                "right_knee": [0.0, 0.0, 0.0],
                "right_ankle": [1.0, 0.0, 0.0],
            },
        ),
        (
            "dorsiflexion_tobillo",
            {
                "right_knee": [0.0, 1.0, 0.0],
                "right_ankle": [0.0, 0.0, 0.0],
                "right_foot": [1.0, 0.0, 0.0],
            },
        ),
        (
            "elevacion_pierna_recta",
            {
                "right_hip": [0.0, 1.0, 0.0],
                "right_knee": [0.0, 0.0, 0.0],
                "right_ankle": [0.0, -1.0, 0.0],
            },
        ),
    ],
)
def test_ejercicios_usan_solo_articulaciones_necesarias(ejercicio, esqueleto):
    resultado = evaluar_ejercicio_rehabilitacion(ejercicio, esqueleto, crear_perfil_demo())

    assert resultado.frame_valido
    assert resultado.angulo_actual is not None


def test_baja_confianza_en_articulacion_requerida_invalida_el_frame():
    esqueleto = esqueleto_codo_90()
    confianza = {
        "right_shoulder": 0.95,
        "right_elbow": 0.95,
        "right_wrist": 0.40,
    }

    resultado = evaluar_ejercicio_rehabilitacion(
        "flexion_codo",
        esqueleto,
        crear_perfil_demo(),
        confianza=confianza,
    )

    assert not resultado.frame_valido
    assert resultado.angulo_actual is None
    assert "hombro, codo y muñeca" in resultado.mensajes[0]


def test_lado_izquierdo_se_evalua_de_frente_sin_puntos_derechos():
    perfil = crear_perfil_demo()
    perfil["ejercicios"]["flexion_codo"]["lado"] = "left"
    esqueleto = {
        "left_shoulder": [1.0, 0.0, 0.0],
        "left_elbow": [0.0, 0.0, 0.0],
        "left_wrist": [0.0, 1.0, 0.0],
    }

    resultado = evaluar_ejercicio_rehabilitacion("flexion_codo", esqueleto, perfil)

    assert resultado.frame_valido
    assert resultado.lado_evaluado == "left"
    assert resultado.angulo_actual == pytest.approx(90.0)


def test_lado_automatico_elige_extremidad_mejor_visible():
    confianza = {
        "right_shoulder": 0.70,
        "right_elbow": 0.72,
        "right_wrist": 0.71,
        "left_shoulder": 0.96,
        "left_elbow": 0.95,
        "left_wrist": 0.94,
    }

    resultado = evaluar_ejercicio_rehabilitacion(
        "flexion_codo",
        esqueleto_codos_bilaterales(),
        crear_perfil_demo(),
        confianza=confianza,
    )

    assert resultado.lado_evaluado == "left"
    assert resultado.angulo_actual == pytest.approx(90.0)


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
