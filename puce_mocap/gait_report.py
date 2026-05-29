"""Reportes CSV simples para el modulo de caminadora."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping

REPORT_FIELDS = [
    "fecha",
    "duracion_segundos",
    "total_frames",
    "frames_validos",
    "porcentaje_verde",
    "porcentaje_amarillo",
    "porcentaje_rojo",
    "promedio_inclinacion_tronco",
    "promedio_asimetria_rodillas",
    "promedio_longitud_paso",
    "estado_global",
    "observaciones",
]

DEFAULT_REPORT_PATH = Path("reports") / "semana_4_gait_report.csv"


def generar_reporte_marcha_csv(resumen: Mapping, ruta_salida: str | Path | None = None) -> Path:
    """Genera un reporte CSV de una sesion de marcha."""
    ruta = Path(ruta_salida) if ruta_salida is not None else DEFAULT_REPORT_PATH
    ruta.parent.mkdir(parents=True, exist_ok=True)

    fila = {campo: resumen.get(campo, "") for campo in REPORT_FIELDS}
    observaciones = fila.get("observaciones", "")
    if isinstance(observaciones, (list, tuple)):
        fila["observaciones"] = " | ".join(str(observacion) for observacion in observaciones)

    with ruta.open("w", newline="", encoding="utf-8") as archivo_csv:
        writer = csv.DictWriter(archivo_csv, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerow(fila)

    return ruta
