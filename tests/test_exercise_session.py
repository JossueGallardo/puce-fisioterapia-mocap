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
        fase="objetivo",
        forma_correcta=True,
        angulo_principal="angulo_rodilla",
    )


def feedback_incorrecto():
    return ExerciseFeedback(
        ejercicio="Sentadilla",
        estado=ESTADO_CORREGIR,
        color=COLOR_ROJO,
        angulos={"angulo_rodilla": 180.0},
        mensajes=["Rodilla fuera del rango 70-100 grados."],
        fase="inicio",
        forma_correcta=None,
        angulo_principal="angulo_rodilla",
    )


def test_sesion_cuenta_un_ciclo_completo_y_forma_evaluable():
    sesion = ExerciseSession("Sentadilla")

    muestras = [(feedback_incorrecto(), indice * 0.1) for indice in range(3)]
    muestras += [(feedback_correcto(), (indice + 3) * 0.1) for indice in range(10)]
    muestras += [(feedback_incorrecto(), (indice + 13) * 0.1) for indice in range(10)]
    for feedback, timestamp in muestras:
        sesion.registrar_feedback(feedback, timestamp)

    assert sesion.total_frames == 23
    assert sesion.frames_correctos == 10
    assert sesion.porcentaje_correcto == 100.0
    assert sesion.repeticiones == 1


def test_sesion_exporta_resumen():
    sesion = ExerciseSession("Sentadilla")
    sesion.registrar_feedback(feedback_incorrecto(), 0.0)
    sesion.registrar_feedback(feedback_correcto(), 0.2)

    resumen = sesion.exportar_resumen()

    assert resumen["ejercicio"] == "Sentadilla"
    assert resumen["total_frames"] == 2
    assert resumen["frames_correctos"] == 1
    assert resumen["porcentaje_correcto"] == 100.0
    assert resumen["repeticiones"] == 0
    assert resumen["session_id"]
    assert "mensajes_principales" in resumen


def test_generar_reporte_csv_con_datos_simulados(tmp_path):
    sesion = ExerciseSession("Sentadilla")
    sesion.registrar_feedback(feedback_incorrecto(), 0.0)
    sesion.registrar_feedback(feedback_correcto(), 0.2)

    ruta = generar_reporte_csv(sesion.exportar_resumen(), tmp_path / "reporte_simulado.csv")

    assert ruta.exists()
    with ruta.open(newline="", encoding="utf-8") as archivo_csv:
        filas = list(csv.DictReader(archivo_csv))

    assert len(filas) == 1
    assert filas[0]["ejercicio"] == "Sentadilla"
    assert filas[0]["total_frames"] == "2"
