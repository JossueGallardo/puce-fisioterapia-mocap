from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from puce_mocap.exercise_report import generar_reporte_csv
from puce_mocap.exercise_rules import evaluar_peso_muerto, evaluar_press_hombro, evaluar_sentadilla
from puce_mocap.exercise_session import ExerciseSession


def esqueleto_sentadilla_correcta():
    return {
        "right_shoulder": [0.0, 2.0, 0.0],
        "right_hip": [0.0, 1.0, 0.0],
        "right_knee": [0.0, 0.0, 0.0],
        "right_ankle": [1.0, 0.0, 0.0],
        "right_foot": [1.0, 1.0, 0.0],
    }


def esqueleto_sentadilla_incorrecta():
    return {
        "right_shoulder": [-1.0, 1.0, 0.0],
        "right_hip": [-1.0, 0.0, 0.0],
        "right_knee": [0.0, 0.0, 0.0],
        "right_ankle": [1.0, 0.0, 0.0],
        "right_foot": [1.0, 1.0, 0.0],
    }


def esqueleto_press_hombro_extendido():
    return {
        "right_shoulder": [0.0, 0.0, 0.0],
        "right_elbow": [0.0, 1.0, 0.0],
        "right_wrist": [0.0, 2.0, 0.0],
    }


def esqueleto_peso_muerto_correcto():
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


def imprimir_feedback(feedback):
    print("\n========================================")
    print(f"Ejercicio: {feedback.ejercicio}")
    print(f"Estado: {feedback.estado} ({feedback.color})")
    print("Angulos / metricas:")
    for nombre, valor in feedback.angulos.items():
        print(f"  - {nombre}: {valor:.2f}")
    print("Retroalimentacion:")
    for mensaje in feedback.mensajes:
        print(f"  - {mensaje}")


def main():
    evaluaciones = [
        evaluar_sentadilla(esqueleto_sentadilla_correcta()),
        evaluar_sentadilla(esqueleto_sentadilla_incorrecta()),
        evaluar_press_hombro(esqueleto_press_hombro_extendido()),
        evaluar_peso_muerto(esqueleto_peso_muerto_correcto()),
    ]

    print("PUCE MoCap - Semana 3 / Modulo de ejercicios con pesas")
    print("Datos simulados. No corresponde a evaluacion clinica.")

    for feedback in evaluaciones:
        imprimir_feedback(feedback)

    sesion = ExerciseSession("Sentadilla")
    for esqueleto in [
        esqueleto_sentadilla_incorrecta(),
        esqueleto_sentadilla_correcta(),
        esqueleto_sentadilla_correcta(),
        esqueleto_sentadilla_incorrecta(),
        esqueleto_sentadilla_correcta(),
    ]:
        sesion.registrar_feedback(evaluar_sentadilla(esqueleto))

    resumen = sesion.exportar_resumen()
    print("\n========================================")
    print("Resumen de sesion simulada:")
    print(f"Ejercicio: {resumen['ejercicio']}")
    print(f"Frames correctos: {resumen['frames_correctos']} / {resumen['total_frames']}")
    print(f"Porcentaje correcto: {resumen['porcentaje_correcto']:.2f}%")
    print(f"Repeticiones estimadas: {resumen['repeticiones']}")

    reporte = generar_reporte_csv(resumen, REPO_ROOT / "reports" / "semana_3_demo_report.csv")
    print(f"Reporte CSV generado: {reporte}")


if __name__ == "__main__":
    main()

