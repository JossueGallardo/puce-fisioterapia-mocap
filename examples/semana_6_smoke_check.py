"""Verificaciones rapidas de Semana 6 sin abrir camara ni interfaces."""

from __future__ import annotations

import importlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def ejecutar_verificaciones() -> list[tuple[str, bool, str]]:
    resultados: list[tuple[str, bool, str]] = []

    modulos = (
        "puce_mocap.angle_utils",
        "puce_mocap.exercise_rules",
        "puce_mocap.gait_analyzer",
        "puce_mocap.rehab_analyzer",
        "puce_mocap.main_menu",
    )
    for nombre in modulos:
        try:
            importlib.import_module(nombre)
            resultados.append((f"Importar {nombre}", True, "disponible"))
        except Exception as exc:  # pragma: no cover - informa fallos del entorno real
            resultados.append((f"Importar {nombre}", False, str(exc)))

    for carpeta in ("docs", "examples", "tests", "reports", "profiles"):
        ruta = REPO_ROOT / carpeta
        resultados.append((f"Carpeta {carpeta}", ruta.is_dir(), str(ruta)))

    for logo in ("logo_puce.png", "logo_fe_alegria.png"):
        ruta = REPO_ROOT / "assets" / logo
        resultados.append((f"Asset {logo}", ruta.is_file(), str(ruta)))

    try:
        import cv2

        resultados.append(("OpenCV", True, getattr(cv2, "__version__", "SIN_VERSION")))
        resultados.append(("cv2.aruco", hasattr(cv2, "aruco"), str(hasattr(cv2, "aruco"))))
    except ImportError as exc:
        resultados.append(("OpenCV", False, str(exc)))
        resultados.append(("cv2.aruco", False, "OpenCV no disponible"))

    try:
        import mediapipe as mp

        binarypb = Path(mp.__file__).parent / "modules" / "pose_landmark" / "pose_landmark_cpu.binarypb"
        resultados.append(("MediaPipe", True, getattr(mp, "__version__", "version no disponible")))
        resultados.append(("pose_landmark_cpu.binarypb", binarypb.exists(), str(binarypb)))
    except ImportError as exc:
        resultados.append(("MediaPipe", False, str(exc)))
        resultados.append(("pose_landmark_cpu.binarypb", False, "MediaPipe no disponible"))

    return resultados


def main() -> int:
    print("PUCE MoCap - Semana 6 / Smoke check sin camara")
    print(f"Ruta oficial: {REPO_ROOT}")
    resultados = ejecutar_verificaciones()
    for nombre, correcto, detalle in resultados:
        estado = "OK" if correcto else "REVISAR"
        print(f"[{estado}] {nombre}: {detalle}")

    fallos = [nombre for nombre, correcto, _ in resultados if not correcto]
    print("\nResumen:")
    if fallos:
        print(f"Se encontraron {len(fallos)} verificaciones por revisar.")
        return 1
    print("Todas las verificaciones rapidas finalizaron correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
