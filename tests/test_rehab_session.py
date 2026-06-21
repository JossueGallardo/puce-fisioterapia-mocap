import csv

import pytest

from puce_mocap.rehab_analyzer import RehabAnalysisResult, evaluar_ejercicio_rehabilitacion
from puce_mocap.rehab_profiles import crear_perfil_demo
from puce_mocap.rehab_report import generar_reporte_rehabilitacion_csv
from puce_mocap.rehab_session import RehabSession


def resultado(angulo_dentro: bool):
    if angulo_dentro:
        esqueleto = {
            "right_shoulder": [1.0, 0.0, 0.0],
            "right_elbow": [0.0, 0.0, 0.0],
            "right_wrist": [0.0, 1.0, 0.0],
        }
    else:
        esqueleto = {
            "right_shoulder": [-1.0, 0.0, 0.0],
            "right_elbow": [0.0, 0.0, 0.0],
            "right_wrist": [1.0, 0.0, 0.0],
        }
    return evaluar_ejercicio_rehabilitacion("flexion_codo", esqueleto, crear_perfil_demo())


def test_sesion_acumula_frames_y_cuenta_ciclo_completo():
    sesion = RehabSession("flexion_codo", "PAC-001")
    incompleto = evaluar_ejercicio_rehabilitacion("flexion_codo", {}, crear_perfil_demo())

    muestras = [(resultado(False), indice * 0.1) for indice in range(3)]
    muestras += [(resultado(True), (indice + 3) * 0.1) for indice in range(10)]
    muestras += [(resultado(False), (indice + 13) * 0.1) for indice in range(10)]
    for actual, timestamp in muestras:
        sesion.registrar_resultado(actual, timestamp)
    sesion.registrar_resultado(incompleto, 2.4)

    assert sesion.total_frames == 24
    assert sesion.frames_validos == 23
    assert sesion.frames_dentro_rango == 10
    assert sesion.porcentaje_dentro_rango == pytest.approx(43.478, rel=1e-3)
    assert sesion.angulo_maximo_alcanzado == pytest.approx(180.0)
    assert sesion.repeticiones_estimadas == 1


@pytest.mark.parametrize("ejercicio", list(crear_perfil_demo()["ejercicios"]))
def test_todos_los_ejercicios_arman_tras_deteccion_tardia_y_cuentan(ejercicio):
    config = crear_perfil_demo()["ejercicios"][ejercicio]
    inicio = config["rango_inicio"]
    objetivo = config["rango_objetivo"]
    angulo_inicio = (inicio["minimo"] + inicio["maximo"]) / 2
    angulo_objetivo = (objetivo["minimo"] + objetivo["maximo"]) / 2
    sesion = RehabSession(ejercicio, "PAC-001", config)

    incompleto = RehabAnalysisResult(
        ejercicio,
        "POSTURA_INCOMPLETA",
        "rojo",
        None,
        objetivo["minimo"],
        objetivo["maximo"],
        False,
        ["No se detecta postura completa."],
    )
    inicio_resultado = RehabAnalysisResult(
        ejercicio,
        "FUERA_DEL_RANGO",
        "amarillo",
        angulo_inicio,
        objetivo["minimo"],
        objetivo["maximo"],
        False,
        ["Posición inicial."],
        forma_correcta=None,
    )
    objetivo_resultado = RehabAnalysisResult(
        ejercicio,
        "DENTRO_DEL_RANGO",
        "verde",
        angulo_objetivo,
        objetivo["minimo"],
        objetivo["maximo"],
        True,
        ["Dentro del rango terapéutico."],
        forma_correcta=True,
    )

    for timestamp in (0.0, 0.2, 0.4):
        sesion.registrar_resultado(incompleto, timestamp)
    sesion.registrar_resultado(inicio_resultado, 0.6)
    for index in range(12):
        sesion.registrar_resultado(objetivo_resultado, 0.8 + index * 0.1)
    for index in range(14):
        sesion.registrar_resultado(inicio_resultado, 2.0 + index * 0.1)

    assert sesion.repeticiones_estimadas == 1


def test_sesion_exporta_resumen():
    sesion = RehabSession("flexion_codo", "PAC-001")
    sesion.registrar_resultado(resultado(True))

    resumen = sesion.exportar_resumen()

    assert resumen["codigo_paciente"] == "PAC-001"
    assert resumen["ejercicio"] == "flexion_codo"
    assert resumen["frames_validos"] == 1
    assert resumen["porcentaje_dentro_rango"] == 100.0
    assert resumen["angulo_minimo_objetivo"] == 30.0


def test_reiniciar_limpia_metricas():
    sesion = RehabSession("flexion_codo", "PAC-001")
    sesion.registrar_resultado(resultado(True))

    sesion.reiniciar()

    assert sesion.total_frames == 0
    assert sesion.frames_validos == 0
    assert sesion.angulo_maximo_alcanzado is None


def test_reporte_csv_incluye_campos_de_perfil_y_sesion(tmp_path):
    perfil = crear_perfil_demo()
    sesion = RehabSession("flexion_codo", perfil["codigo_paciente"])
    sesion.registrar_resultado(resultado(True))

    ruta = generar_reporte_rehabilitacion_csv(sesion.exportar_resumen(), perfil, tmp_path / "rehab.csv")

    with ruta.open(newline="", encoding="utf-8") as archivo:
        fila = next(csv.DictReader(archivo))
    assert fila["codigo_paciente"] == "PAC-001"
    assert fila["nombre_paciente"] == "Paciente de prueba"
    assert fila["ejercicio"] == "flexion_codo"
    assert fila["porcentaje_dentro_rango"] == "100.0"
    assert fila["comparacion_sesion_anterior"] == "Sin sesión anterior comparable."


def test_reporte_compara_con_sesion_anterior_del_mismo_ejercicio(tmp_path):
    perfil = crear_perfil_demo()
    ruta = tmp_path / "rehab.csv"
    resumen_anterior = {
        "fecha": "2026-06-01T10:00:00",
        "codigo_paciente": "PAC-001",
        "ejercicio": "flexion_codo",
        "angulo_minimo_objetivo": 30.0,
        "angulo_maximo_objetivo": 130.0,
        "angulo_maximo_alcanzado": 80.0,
        "repeticiones_estimadas": 1,
        "porcentaje_dentro_rango": 50.0,
        "observaciones": [],
    }
    generar_reporte_rehabilitacion_csv(resumen_anterior, perfil, ruta)

    sesion = RehabSession("flexion_codo", "PAC-001")
    sesion.registrar_resultado(resultado(True))
    generar_reporte_rehabilitacion_csv(sesion.exportar_resumen(), perfil, ruta)

    with ruta.open(newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == 2
    assert filas[-1]["comparacion_sesion_anterior"] == "Aumento de 10.00 grados respecto a la sesión anterior."
