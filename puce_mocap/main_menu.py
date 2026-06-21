"""Entrada ligera del menú Qt de PUCE MoCap."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULOS = {
    "1": ("Módulo 1 - Ejercicios con pesas", "puce_mocap.modulo_pesas_app"),
    "2": ("Módulo 2 - Rehabilitación", "puce_mocap.modulo_rehabilitacion_app"),
    "3": ("Módulo 3 - Caminadora", "puce_mocap.modulo_caminadora_app"),
    "4": ("FreeMoCap original", "freemocap"),
}


def comando_modulo(opcion: str) -> list[str]:
    if opcion not in MODULOS:
        raise ValueError(f"Opción de módulo no válida: {opcion}.")
    return [sys.executable, "-m", MODULOS[opcion][1]]


def ejecutar_modulo(
    opcion: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    """Compatibilidad para automatizaciones antiguas; la GUI usa QProcess."""
    try:
        process = runner(comando_modulo(opcion), cwd=REPO_ROOT, check=False)
    except OSError:
        return 1
    return int(getattr(process, "returncode", 0))


def verificar_entorno() -> dict[str, tuple[bool, str]]:
    results = {}
    try:
        import cv2

        results["OpenCV"] = (True, f"Version {cv2.__version__}")
        results["cv2.aruco"] = (hasattr(cv2, "aruco"), "Disponible" if hasattr(cv2, "aruco") else "No disponible")
    except ImportError as exc:
        results["OpenCV"] = (False, str(exc))
        results["cv2.aruco"] = (False, "No disponible")
    try:
        import mediapipe as mp

        results["MediaPipe"] = (True, f"Version {getattr(mp, '__version__', 'disponible')}")
    except ImportError as exc:
        results["MediaPipe"] = (False, str(exc))
    try:
        import PySide6

        results["PySide6"] = (True, f"Version {PySide6.__version__}")
    except ImportError as exc:
        results["PySide6"] = (False, str(exc))
    return results


def ejecutar_pytest(
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> tuple[int, str]:
    try:
        process = runner(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return 1, f"No se pudo ejecutar pytest: {exc}"
    output = f"{getattr(process, 'stdout', '')}\n{getattr(process, 'stderr', '')}".strip()
    summary = next((line.strip() for line in reversed(output.splitlines()) if "passed" in line or "failed" in line), output[-500:])
    return int(getattr(process, "returncode", 0)), summary


def main() -> int:
    from puce_mocap.qt_app import run

    return run("menu")


if __name__ == "__main__":
    raise SystemExit(main())
