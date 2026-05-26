from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from puce_mocap.freemocap_adapter import evaluar_ejercicio_freemocap, normalizar_articulaciones_freemocap


def datos_freemocap_simulados():
    """Datos 3D ficticios con nombres parecidos a exportaciones de mocap."""
    return {
        "rightShoulder": [0.0, 2.0, 0.0],
        "leftShoulder": [-0.4, 2.0, 0.0],
        "rightHip": [0.0, 1.0, 0.0],
        "leftHip": [-0.4, 1.0, 0.0],
        "rightKnee": [0.0, 0.0, 0.0],
        "leftKnee": [-0.4, 0.0, 0.0],
        "rightAnkle": [1.0, 0.0, 0.0],
        "leftAnkle": [-0.4, -1.0, 0.0],
        "right_foot_index": [1.0, 1.0, 0.0],
        "rightElbow": [0.0, 2.8, 0.0],
        "rightWrist": [0.0, 3.6, 0.0],
    }


def main():
    datos = datos_freemocap_simulados()
    normalizados = normalizar_articulaciones_freemocap(datos)
    feedback = evaluar_ejercicio_freemocap(datos, "sentadilla")

    print("PUCE MoCap - Demo adaptador FreeMoCap")
    print("Datos simulados. No corresponden a una sesion real de paciente.")
    print("\nArticulaciones normalizadas:")
    for nombre in sorted(normalizados):
        print(f"  - {nombre}: {normalizados[nombre]}")

    print("\nEvaluacion:")
    print(f"Ejercicio: {feedback.ejercicio}")
    print(f"Estado: {feedback.estado} ({feedback.color})")
    for nombre, valor in feedback.angulos.items():
        print(f"  - {nombre}: {valor:.2f}")
    for mensaje in feedback.mensajes:
        print(f"  - {mensaje}")


if __name__ == "__main__":
    main()

