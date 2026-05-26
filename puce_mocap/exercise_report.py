"""Reportes CSV simples para el modulo de ejercicios con pesas."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Mapping

REPORT_FIELDS = [
    "fecha",
    "ejercicio",
    "total_frames",
    "frames_correctos",
    "porcentaje_correcto",
    "repeticiones",
    "mensajes_principales",
]


def generar_reporte_csv(resumen: Mapping, ruta_salida: str | Path | None = None) -> Path:
    """Genera un reporte CSV de una sesion de ejercicio."""
    if ruta_salida is None:
        marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = Path("reports") / f"exercise_session_{marca_tiempo}.csv"
    else:
        ruta = Path(ruta_salida)

    ruta.parent.mkdir(parents=True, exist_ok=True)

    fila = {campo: resumen.get(campo, "") for campo in REPORT_FIELDS}
    mensajes = fila.get("mensajes_principales", "")
    if isinstance(mensajes, (list, tuple)):
        fila["mensajes_principales"] = " | ".join(str(mensaje) for mensaje in mensajes)

    with ruta.open("w", newline="", encoding="utf-8") as archivo_csv:
        writer = csv.DictWriter(archivo_csv, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerow(fila)

    return ruta

