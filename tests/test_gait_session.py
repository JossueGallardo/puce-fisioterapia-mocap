import csv

from puce_mocap.gait_analyzer import analizar_marcha
from puce_mocap.gait_report import generar_reporte_marcha_csv
from puce_mocap.gait_session import GaitSession


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


def test_sesion_marcha_acumula_frames_validos_y_alertas():
    sesion = GaitSession()

    sesion.registrar_resultado(analizar_marcha(esqueleto_marcha_normal()))
    sesion.registrar_resultado(analizar_marcha(esqueleto_con_asimetria()))
    sesion.registrar_resultado(analizar_marcha({"right_hip": [0.0, 1.0, 0.0]}))

    assert sesion.total_frames == 3
    assert sesion.frames_validos == 2
    assert sesion.alertas_verdes == 1
    assert sesion.alertas_amarillas == 1
    assert sesion.alertas_rojas == 0
    assert sesion.porcentaje_verde == 50.0
    assert sesion.porcentaje_amarillo == 50.0


def test_sesion_marcha_exporta_resumen():
    sesion = GaitSession()
    sesion.registrar_resultado(analizar_marcha(esqueleto_marcha_normal()))

    resumen = sesion.exportar_resumen(duracion_segundos=12.5)

    assert resumen["duracion_segundos"] == 12.5
    assert resumen["total_frames"] == 1
    assert resumen["frames_validos"] == 1
    assert resumen["porcentaje_verde"] == 100.0
    assert resumen["promedio_inclinacion_tronco"] == 0.0
    assert resumen["promedio_asimetria_rodillas"] == 0.0
    assert resumen["promedio_longitud_paso"] == 0.4
    assert resumen["estado_global"] == "NORMAL"


def test_reporte_marcha_csv(tmp_path):
    sesion = GaitSession()
    sesion.registrar_resultado(analizar_marcha(esqueleto_marcha_normal()))

    ruta = generar_reporte_marcha_csv(sesion.exportar_resumen(duracion_segundos=10.0), tmp_path / "gait.csv")

    assert ruta.exists()
    with ruta.open(newline="", encoding="utf-8") as archivo_csv:
        filas = list(csv.DictReader(archivo_csv))

    assert len(filas) == 1
    assert filas[0]["frames_validos"] == "1"
    assert filas[0]["estado_global"] == "NORMAL"
