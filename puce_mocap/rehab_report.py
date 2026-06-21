"""Reporte CSV del Módulo 2 de rehabilitación."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping

from puce_mocap.app_paths import reports_dir


REPORT_FIELDS = [
    "fecha",
    "codigo_paciente",
    "nombre_paciente",
    "lesion",
    "ejercicio",
    "angulo_minimo_objetivo",
    "angulo_maximo_objetivo",
    "angulo_maximo_alcanzado",
    "repeticiones_realizadas",
    "porcentaje_dentro_rango",
    "comparacion_sesion_anterior",
    "observacion",
]

DEFAULT_REPORT_PATH = reports_dir() / "semana_5_rehab_report.csv"


def generar_reporte_rehabilitacion_csv(  # noqa: C901
    resumen: Mapping[str, Any],
    perfil: Mapping[str, Any],
    ruta_salida: str | Path | None = None,
) -> Path:
    """Agrega una sesión al CSV y compara el ángulo máximo cuando es posible."""
    ruta = Path(ruta_salida) if ruta_salida is not None else DEFAULT_REPORT_PATH
    ruta.parent.mkdir(parents=True, exist_ok=True)

    fila_anterior = None
    campos_existentes = None
    filas_anteriores: list[dict[str, str]] = []
    if ruta.exists() and ruta.stat().st_size > 0:
        with ruta.open(newline="", encoding="utf-8") as archivo_existente:
            lector = csv.DictReader(archivo_existente)
            campos_existentes = lector.fieldnames
            filas_anteriores = list(lector)
        if filas_anteriores:
            fila_anterior = filas_anteriores[-1]

    observaciones = resumen.get("observaciones", [])
    if isinstance(observaciones, (list, tuple)):
        observaciones = " | ".join(str(observacion) for observacion in observaciones)
    observacion_perfil = str(perfil.get("observaciones", "")).strip()
    observacion = " | ".join(parte for parte in (observacion_perfil, str(observaciones).strip()) if parte)

    ejercicio = str(resumen.get("ejercicio", ""))
    configuracion = perfil.get("ejercicios", {}).get(ejercicio, {})
    rango_objetivo = configuracion.get("rango_objetivo", {})
    angulo_actual = resumen.get("angulo_maximo_alcanzado")
    comparacion = "Sin sesión anterior comparable."
    if fila_anterior and fila_anterior.get("ejercicio") == ejercicio:
        try:
            angulo_anterior = float(fila_anterior["angulo_maximo_alcanzado"])
            diferencia = float(angulo_actual) - angulo_anterior
            if diferencia > 0:
                comparacion = f"Aumento de {diferencia:.2f} grados respecto a la sesión anterior."
            elif diferencia < 0:
                comparacion = f"Disminución de {abs(diferencia):.2f} grados respecto a la sesión anterior."
            else:
                comparacion = "Sin cambio en el ángulo máximo respecto a la sesión anterior."
        except (TypeError, ValueError, KeyError):
            comparacion = "Sesión anterior sin ángulo máximo comparable."

    fila = {
        "fecha": resumen.get("fecha", ""),
        "codigo_paciente": resumen.get("codigo_paciente", perfil.get("codigo_paciente", "")),
        "nombre_paciente": perfil.get("nombre", ""),
        "lesion": perfil.get("lesion", ""),
        "ejercicio": ejercicio,
        "angulo_minimo_objetivo": resumen.get("angulo_minimo_objetivo")
        if resumen.get("angulo_minimo_objetivo") is not None
        else configuracion.get("angulo_minimo", rango_objetivo.get("minimo", "")),
        "angulo_maximo_objetivo": resumen.get("angulo_maximo_objetivo")
        if resumen.get("angulo_maximo_objetivo") is not None
        else configuracion.get("angulo_maximo", rango_objetivo.get("maximo", "")),
        "angulo_maximo_alcanzado": angulo_actual if angulo_actual is not None else "",
        "repeticiones_realizadas": resumen.get("repeticiones_estimadas", 0),
        "porcentaje_dentro_rango": resumen.get("porcentaje_dentro_rango", 0.0),
        "comparacion_sesion_anterior": comparacion,
        "observacion": observacion,
    }

    if campos_existentes and campos_existentes != REPORT_FIELDS:
        with ruta.open("w", newline="", encoding="utf-8") as archivo_migrado:
            writer = csv.DictWriter(archivo_migrado, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            for fila_existente in filas_anteriores:
                writer.writerow({campo: fila_existente.get(campo, "") for campo in REPORT_FIELDS})

    escribir_encabezado = not ruta.exists() or ruta.stat().st_size == 0
    with ruta.open("a", newline="", encoding="utf-8") as archivo_csv:
        writer = csv.DictWriter(archivo_csv, fieldnames=REPORT_FIELDS)
        if escribir_encabezado:
            writer.writeheader()
        writer.writerow(fila)
    return ruta
