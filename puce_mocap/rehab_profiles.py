"""Perfiles JSON versionados para ejercicios de rehabilitación."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from puce_mocap.movement import AngleRange, MovementDefinition


EJERCICIOS_REHABILITACION = (
    "flexion_codo",
    "abduccion_hombro",
    "rotacion_muneca",
    "extension_rodilla",
    "dorsiflexion_tobillo",
    "elevacion_pierna_recta",
)

CAMPOS_OBLIGATORIOS = ("nombre", "codigo_paciente", "lesion", "observaciones", "ejercicios")
CAMPOS_SENSIBLES = {"cedula", "telefono", "direccion", "correo", "email"}
RANGOS_INICIO_PREDETERMINADOS = {
    "flexion_codo": (160.0, 180.0),
    "abduccion_hombro": (0.0, 20.0),
    "rotacion_muneca": (-10.0, 10.0),
    "extension_rodilla": (80.0, 120.0),
    "dorsiflexion_tobillo": (0.0, 5.0),
    "elevacion_pierna_recta": (0.0, 10.0),
}


def _config(
    inicio: tuple[float, float],
    objetivo: tuple[float, float],
    repeticiones: int,
    *,
    lado: str = "right",
) -> dict[str, Any]:
    return {
        "rango_inicio": {"minimo": inicio[0], "maximo": inicio[1]},
        "rango_objetivo": {"minimo": objetivo[0], "maximo": objetivo[1]},
        "repeticiones_objetivo": repeticiones,
        "lado": lado,
        "histeresis_grados": 3.0,
        "permanencia_ms": 200,
        "ciclo_minimo_ms": 600,
    }


PERFIL_DEMO = {
    "schema_version": 2,
    "nombre": "Paciente de prueba",
    "codigo_paciente": "PAC-001",
    "lesion": "Caso ficticio de rehabilitación",
    "observaciones": "Perfil demo sin datos reales",
    "ejercicios": {
        "flexion_codo": _config((160, 180), (30, 130), 10),
        "abduccion_hombro": _config((0, 20), (45, 100), 8),
        "rotacion_muneca": _config((-10, 10), (45, 90), 8),
        "extension_rodilla": _config((80, 120), (160, 180), 10),
        "dorsiflexion_tobillo": _config((0, 5), (10, 25), 10),
        "elevacion_pierna_recta": _config((0, 10), (30, 60), 8),
    },
}


def _es_numero(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _normalizar_lado(lado: str) -> str:
    if lado in {"right", "derecho", "derecha"}:
        return "right"
    if lado in {"left", "izquierdo", "izquierda"}:
        return "left"
    raise ValueError("El lado configurado debe ser derecho/right o izquierdo/left.")


def _leer_rango(valor: Any, nombre: str) -> AngleRange:
    if not isinstance(valor, Mapping):
        raise ValueError(f"{nombre} debe ser un objeto con mínimo y máximo.")
    minimo = valor.get("minimo")
    maximo = valor.get("maximo")
    if not _es_numero(minimo) or not _es_numero(maximo):
        raise ValueError(f"Los límites de {nombre} deben ser numéricos.")
    return AngleRange(float(minimo), float(maximo))


def movimiento_desde_config(configuracion: Mapping[str, Any]) -> MovementDefinition:
    return MovementDefinition(
        start_range=_leer_rango(configuracion["rango_inicio"], "rango_inicio"),
        target_range=_leer_rango(configuracion["rango_objetivo"], "rango_objetivo"),
        hysteresis_deg=float(configuracion.get("histeresis_grados", 3.0)),
        dwell_seconds=float(configuracion.get("permanencia_ms", 200)) / 1000.0,
        min_cycle_seconds=float(configuracion.get("ciclo_minimo_ms", 600)) / 1000.0,
    )


def normalizar_perfil_paciente(perfil: Mapping[str, Any]) -> dict[str, Any]:  # noqa: C901
    """Valida un perfil v1/v2 y devuelve una copia normalizada al esquema v2."""
    if not isinstance(perfil, Mapping):
        raise ValueError("El perfil debe ser un objeto JSON.")
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in perfil:
            raise ValueError(f"Falta el campo obligatorio: {campo}.")

    sensibles = CAMPOS_SENSIBLES.intersection(str(clave).lower() for clave in perfil)
    if sensibles:
        raise ValueError(f"El perfil no debe incluir datos sensibles: {', '.join(sorted(sensibles))}.")
    for campo in ("nombre", "codigo_paciente", "lesion", "observaciones"):
        if not isinstance(perfil[campo], str) or not perfil[campo].strip():
            raise ValueError(f"El campo {campo} debe ser texto no vacio.")

    ejercicios = perfil["ejercicios"]
    if not isinstance(ejercicios, Mapping) or not ejercicios:
        raise ValueError("El campo ejercicios debe contener al menos un ejercicio.")

    normalizado = {campo: deepcopy(perfil[campo]) for campo in CAMPOS_OBLIGATORIOS if campo != "ejercicios"}
    normalizado["schema_version"] = 2
    normalizado["ejercicios"] = {}
    for nombre, configuracion_original in ejercicios.items():
        if nombre not in EJERCICIOS_REHABILITACION:
            raise ValueError(f"Ejercicio no soportado en el perfil: {nombre}.")
        if not isinstance(configuracion_original, Mapping):
            raise ValueError(f"La configuración de {nombre} debe ser un objeto JSON.")
        configuracion = dict(configuracion_original)
        if "rango_objetivo" not in configuracion:
            minimo = configuracion.get("angulo_minimo")
            maximo = configuracion.get("angulo_maximo")
            if not _es_numero(minimo) or not _es_numero(maximo):
                raise ValueError(f"El perfil legado de {nombre} requiere angulo_minimo y angulo_maximo.")
            configuracion["rango_objetivo"] = {"minimo": float(minimo), "maximo": float(maximo)}
        configuracion.pop("angulo_minimo", None)
        configuracion.pop("angulo_maximo", None)
        if "rango_inicio" not in configuracion:
            minimo, maximo = RANGOS_INICIO_PREDETERMINADOS[nombre]
            configuracion["rango_inicio"] = {"minimo": minimo, "maximo": maximo}

        repeticiones = configuracion.get("repeticiones_objetivo")
        if not isinstance(repeticiones, int) or isinstance(repeticiones, bool) or repeticiones <= 0:
            raise ValueError(f"repeticiones_objetivo de {nombre} debe ser un entero positivo.")
        configuracion["lado"] = _normalizar_lado(str(configuracion.get("lado", "right")))
        configuracion.setdefault("histeresis_grados", 3.0)
        configuracion.setdefault("permanencia_ms", 200)
        configuracion.setdefault("ciclo_minimo_ms", 600)
        movimiento_desde_config(configuracion)
        normalizado["ejercicios"][nombre] = configuracion
    return normalizado


def validar_perfil_paciente(perfil: Mapping[str, Any]) -> bool:
    normalizar_perfil_paciente(perfil)
    return True


def crear_perfil_demo() -> dict[str, Any]:
    return deepcopy(PERFIL_DEMO)


def cargar_perfil_paciente(ruta_json: str | Path) -> dict[str, Any]:
    ruta = Path(ruta_json)
    try:
        with ruta.open(encoding="utf-8") as archivo:
            perfil = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise ValueError(f"El archivo JSON no es válido: {exc.msg}.") from exc
    return normalizar_perfil_paciente(perfil)


def guardar_perfil_paciente(perfil: Mapping[str, Any], ruta_json: str | Path) -> Path:
    normalizado = normalizar_perfil_paciente(perfil)
    ruta = Path(ruta_json)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(normalizado, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    return ruta
