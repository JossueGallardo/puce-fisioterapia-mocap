import importlib
from pathlib import Path

import pytest

from examples.semana_6_smoke_check import ejecutar_verificaciones


@pytest.mark.parametrize(
    "nombre_modulo",
    [
        "puce_mocap.angle_utils",
        "puce_mocap.exercise_rules",
        "puce_mocap.gait_analyzer",
        "puce_mocap.rehab_analyzer",
        "puce_mocap.main_menu",
        "puce_mocap.modulo_rehabilitacion_app",
    ],
)
def test_imports_principales_no_abren_camara(nombre_modulo):
    assert importlib.import_module(nombre_modulo) is not None


def test_smoke_check_incluye_carpetas_y_aruco():
    resultados = {nombre: correcto for nombre, correcto, _ in ejecutar_verificaciones()}

    assert resultados["Carpeta docs"]
    assert resultados["Carpeta profiles"]
    assert resultados["cv2.aruco"]


def test_perfil_demo_existe_en_repositorio():
    raiz = Path(__file__).resolve().parents[1]

    assert (raiz / "profiles" / "paciente_demo.json").is_file()
