from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from puce_mocap.gait_analyzer import analizar_marcha


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


def imprimir_resultado(nombre: str, esqueleto: dict[str, list[float]]) -> None:
    resultado = analizar_marcha(esqueleto)
    print("\n========================================")
    print(nombre)
    print(f"Estado: {resultado.estado} ({resultado.color})")
    print("Metricas:")
    for metrica, valor in resultado.metricas.items():
        texto_valor = "N/D" if valor is None else f"{valor:.2f}"
        print(f"  - {metrica}: {texto_valor}")
    print("Retroalimentacion:")
    for mensaje in resultado.mensajes:
        print(f"  - {mensaje}")


def main() -> None:
    print("PUCE MoCap - Semana 4 / Modulo de caminadora")
    print("Datos simulados. No corresponde a evaluacion clinica.")

    casos = [
        ("Marcha normal simulada", esqueleto_marcha_normal()),
        ("Marcha con asimetria de rodillas", esqueleto_con_asimetria()),
        ("Marcha con inclinacion elevada del tronco", esqueleto_con_tronco_inclinado()),
    ]
    for nombre, esqueleto in casos:
        imprimir_resultado(nombre, esqueleto)


if __name__ == "__main__":
    main()
