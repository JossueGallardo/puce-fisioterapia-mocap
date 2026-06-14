import json

import pytest

from puce_mocap.rehab_profiles import (
    cargar_perfil_paciente,
    crear_perfil_demo,
    guardar_perfil_paciente,
    validar_perfil_paciente,
)


def test_crear_y_validar_perfil_demo():
    perfil = crear_perfil_demo()

    assert validar_perfil_paciente(perfil)
    assert perfil["codigo_paciente"] == "PAC-001"
    assert "flexion_codo" in perfil["ejercicios"]


def test_guardar_y_cargar_perfil_demo(tmp_path):
    ruta = guardar_perfil_paciente(crear_perfil_demo(), tmp_path / "perfil.json")
    cargado = cargar_perfil_paciente(ruta)

    assert cargado["nombre"] == "Paciente de prueba"
    assert cargado["ejercicios"]["extension_rodilla"]["angulo_maximo"] == 180


def test_validar_perfil_error_si_falta_campo_obligatorio():
    perfil = crear_perfil_demo()
    perfil.pop("codigo_paciente")

    with pytest.raises(ValueError, match="codigo_paciente"):
        validar_perfil_paciente(perfil)


def test_cargar_perfil_rechaza_json_invalido(tmp_path):
    ruta = tmp_path / "invalido.json"
    ruta.write_text(json.dumps({"nombre": "Demo"}), encoding="utf-8")

    with pytest.raises(ValueError, match="campo obligatorio"):
        cargar_perfil_paciente(ruta)
