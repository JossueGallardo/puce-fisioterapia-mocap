import csv

from puce_mocap.exercise_report import generar_reporte_csv
from puce_mocap.exercise_rules import COLOR_ROJO, COLOR_VERDE, ESTADO_CORRECTO, ESTADO_CORREGIR, ExerciseFeedback
from puce_mocap.exercise_session import ExerciseSession


def feedback_correcto():
    return ExerciseFeedback(
        ejercicio="Sentadilla",
        estado=ESTADO_CORRECTO,
        color=COLOR_VERDE,
        angulos={"angulo_rodilla": 90.0},
        mensajes=["Postura correcta."],
    )


def feedback_incorrecto():
    return ExerciseFeedback(
        ejercicio="Sentadilla",
        estado=ESTADO_CORREGIR,
        color=COLOR_ROJO,
        angulos={"angulo_rodilla": 180.0},
        mensajes=["Rodilla fuera del rango 70-100 grados."],
    )


def test_sesion_cuenta_frames_correctos_porcentaje_y_repeticiones():
    sesion = ExerciseSession("Sentadilla")

    for feedback in [
        feedback_incorrecto(),
        feedback_correcto(),
        feedback_correcto(),
        feedback_incorrecto(),
        feedback_correcto(),
    ]:
        sesion.registrar_feedback(feedback)

    assert sesion.total_frames == 5
    assert sesion.frames_correctos == 3
    assert sesion.porcentaje_correcto == 60.0
    assert sesion.repeticiones == 2


def test_sesion_exporta_resumen():
    sesion = ExerciseSession("Sentadilla")
    sesion.registrar_feedback(feedback_incorrecto())
    sesion.registrar_feedback(feedback_correcto())

    resumen = sesion.exportar_resumen()

    assert resumen["ejercicio"] == "Sentadilla"
    assert resumen["total_frames"] == 2
    assert resumen["frames_correctos"] == 1
    assert resumen["porcentaje_correcto"] == 50.0
    assert resumen["repeticiones"] == 1
    assert "mensajes_principales" in resumen


def test_generar_reporte_csv_con_datos_simulados(tmp_path):
    sesion = ExerciseSession("Sentadilla")
    sesion.registrar_feedback(feedback_incorrecto())
    sesion.registrar_feedback(feedback_correcto())

    ruta = generar_reporte_csv(sesion.exportar_resumen(), tmp_path / "reporte_simulado.csv")

    assert ruta.exists()
    with ruta.open(newline="", encoding="utf-8") as archivo_csv:
        filas = list(csv.DictReader(archivo_csv))

    assert len(filas) == 1
    assert filas[0]["ejercicio"] == "Sentadilla"
    assert filas[0]["total_frames"] == "2"

