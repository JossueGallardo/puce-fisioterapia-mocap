"""Perfiles JSON ficticios para el Modulo 2 de rehabilitacion."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping


EJERCICIOS_REHABILITACION = (
    "flexion_codo",
    "abduccion_hombro",
    "rotacion_muneca",
    "extension_rodilla",
    "dorsiflexion_tobillo",
    "elevacion_pierna_recta",
)

CAMPOS_OBLIGATORIOS = ("nombre", "codigo_paciente", "lesion", "observaciones", "ejercicios")
CAMPOS_EJERCICIO = ("angulo_minimo", "angulo_maximo", "repeticiones_objetivo")
CAMPOS_SENSIBLES = {"cedula", "telefono", "direccion", "correo", "email"}


PERFIL_DEMO = {
    "nombre": "Paciente de prueba",
    "codigo_paciente": "PAC-001",
    "lesion": "Caso ficticio de rehabilitacion",
    "observaciones": "Perfil demo sin datos reales",
    "ejercicios": {
        "flexion_codo": {"angulo_minimo": 30, "angulo_maximo": 130, "repeticiones_objetivo": 10},
        "abduccion_hombro": {"angulo_minimo": 45, "angulo_maximo": 100, "repeticiones_objetivo": 8},
        "rotacion_muneca": {"angulo_minimo": 70, "angulo_maximo": 170, "repeticiones_objetivo": 8},
        "extension_rodilla": {"angulo_minimo": 160, "angulo_maximo": 180, "repeticiones_objetivo": 10},
        "dorsiflexion_tobillo": {"angulo_minimo": 0, "angulo_maximo": 25, "repeticiones_objetivo": 10},
        "elevacion_pierna_recta": {"angulo_minimo": 30, "angulo_maximo": 60, "repeticiones_objetivo": 8},
    },
}


def _es_numero(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def validar_perfil_paciente(perfil: Mapping[str, Any]) -> bool:
    """Valida la estructura minima de un perfil ficticio."""
    if not isinstance(perfil, Mapping):
        raise ValueError("El perfil debe ser un objeto JSON.")

    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in perfil:
            raise ValueError(f"Falta el campo obligatorio: {campo}.")

    sensibles_presentes = CAMPOS_SENSIBLES.intersection(str(clave).lower() for clave in perfil)
    if sensibles_presentes:
        campos = ", ".join(sorted(sensibles_presentes))
        raise ValueError(f"El perfil no debe incluir datos sensibles: {campos}.")

    for campo in ("nombre", "codigo_paciente", "lesion", "observaciones"):
        if not isinstance(perfil[campo], str) or not perfil[campo].strip():
            raise ValueError(f"El campo {campo} debe ser texto no vacio.")

    ejercicios = perfil["ejercicios"]
    if not isinstance(ejercicios, Mapping) or not ejercicios:
        raise ValueError("El campo ejercicios debe contener al menos un ejercicio configurado.")

    for nombre, configuracion in ejercicios.items():
        if nombre not in EJERCICIOS_REHABILITACION:
            raise ValueError(f"Ejercicio no soportado en el perfil: {nombre}.")
        if not isinstance(configuracion, Mapping):
            raise ValueError(f"La configuracion de {nombre} debe ser un objeto JSON.")
        for campo in CAMPOS_EJERCICIO:
            if campo not in configuracion:
                raise ValueError(f"Falta {campo} en el ejercicio {nombre}.")

        minimo = configuracion["angulo_minimo"]
        maximo = configuracion["angulo_maximo"]
        repeticiones = configuracion["repeticiones_objetivo"]
        if not _es_numero(minimo) or not _es_numero(maximo):
            raise ValueError(f"Los angulos de {nombre} deben ser numericos.")
        if float(minimo) > float(maximo):
            raise ValueError(f"angulo_minimo no puede superar angulo_maximo en {nombre}.")
        if not isinstance(repeticiones, int) or isinstance(repeticiones, bool) or repeticiones <= 0:
            raise ValueError(f"repeticiones_objetivo de {nombre} debe ser un entero positivo.")

        lado = configuracion.get("lado", "right")
        if lado not in {"right", "left", "derecho", "izquierdo"}:
            raise ValueError(f"El lado configurado para {nombre} no es valido.")

    return True


def crear_perfil_demo() -> dict[str, Any]:
    """Retorna una copia independiente del perfil ficticio incluido."""
    return deepcopy(PERFIL_DEMO)


def cargar_perfil_paciente(ruta_json: str | Path) -> dict[str, Any]:
    """Carga y valida un perfil de paciente ficticio desde JSON."""
    ruta = Path(ruta_json)
    try:
        with ruta.open(encoding="utf-8") as archivo:
            perfil = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise ValueError(f"El archivo JSON no es valido: {exc.msg}.") from exc

    validar_perfil_paciente(perfil)
    return perfil


def guardar_perfil_paciente(perfil: Mapping[str, Any], ruta_json: str | Path) -> Path:
    """Valida y guarda un perfil ficticio en formato JSON legible."""
    validar_perfil_paciente(perfil)
    ruta = Path(ruta_json)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(dict(perfil), archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return ruta
