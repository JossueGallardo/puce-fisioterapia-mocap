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
    assert perfil["ejercicios"]["flexion_codo"]["lado"] == "auto"
    assert perfil["ejercicios"]["abduccion_hombro"]["rango_objetivo"] == {
        "minimo": 100,
        "maximo": 120,
    }
    assert perfil["ejercicios"]["abduccion_hombro"]["excursion_minima_grados"] == 70.0


def test_guardar_y_cargar_perfil_demo(tmp_path):
    ruta = guardar_perfil_paciente(crear_perfil_demo(), tmp_path / "perfil.json")
    cargado = cargar_perfil_paciente(ruta)

    assert cargado["nombre"] == "Paciente de prueba"
    assert cargado["schema_version"] == 2
    assert cargado["ejercicios"]["extension_rodilla"]["rango_objetivo"]["maximo"] == 180


def test_perfil_v1_se_migra_en_memoria_a_v2():
    perfil = crear_perfil_demo()
    configuracion = perfil["ejercicios"]["flexion_codo"]
    perfil.pop("schema_version")
    perfil["ejercicios"]["flexion_codo"] = {
        "angulo_minimo": configuracion["rango_objetivo"]["minimo"],
        "angulo_maximo": configuracion["rango_objetivo"]["maximo"],
        "repeticiones_objetivo": 10,
    }

    from puce_mocap.rehab_profiles import normalizar_perfil_paciente

    migrado = normalizar_perfil_paciente(perfil)
    assert migrado["schema_version"] == 2
    assert migrado["ejercicios"]["flexion_codo"]["rango_inicio"] == {"minimo": 160.0, "maximo": 180.0}


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


def test_perfil_acepta_seleccion_automatica_de_extremidad():
    from puce_mocap.rehab_profiles import normalizar_perfil_paciente

    perfil = crear_perfil_demo()
    perfil["ejercicios"]["flexion_codo"]["lado"] = "automático"

    normalizado = normalizar_perfil_paciente(perfil)

    assert normalizado["ejercicios"]["flexion_codo"]["lado"] == "auto"
