import csv

from puce_mocap.reports_v2 import (
    export_rehab_sessions,
    export_weight_sessions,
    sanitize_csv_value,
)
from puce_mocap.rehab_profiles import crear_perfil_demo


def test_sanitiza_formulas_de_hoja_de_calculo():
    assert sanitize_csv_value("=HYPERLINK('x')") == "'=HYPERLINK('x')"
    assert sanitize_csv_value("Paciente de prueba") == "Paciente de prueba"


def test_reporte_pesas_v2_incluye_contexto_y_session_id(tmp_path):
    path = export_weight_sessions(
        [
            {
                "session_id": "S-1",
                "fecha": "2026-06-21T10:00:00",
                "fuente_datos": "freemocap_session",
                "codigo_paciente": "PAC-001",
                "nombre_paciente": "Paciente ficticio",
                "lesion": "Seguimiento ficticio",
                "observaciones_paciente": "Sin datos reales",
                "ejercicio": "Sentadilla",
                "total_frames": 10,
                "frames_evaluables_forma": 4,
                "frames_correctos": 4,
                "porcentaje_correcto": 100.0,
                "repeticiones": 1,
            }
        ],
        tmp_path / "pesas.csv",
    )

    with path.open(newline="", encoding="utf-8") as stream:
        row = next(csv.DictReader(stream))
    assert row["session_id"] == "S-1"
    assert row["nombre_paciente"] == "Paciente ficticio"
    assert row["institucion"] == "Pontificia Universidad Católica del Ecuador"
    assert row["licencia"] == "AGPLv3"


def test_comparacion_rehab_busca_mismo_paciente_y_ejercicio(tmp_path):
    path = tmp_path / "rehab.csv"
    profile = crear_perfil_demo()
    base = {
        "session_id": "S-1",
        "fecha": "2026-06-01T10:00:00",
        "fuente_datos": "mediapipe_live",
        "codigo_paciente": "PAC-001",
        "ejercicio": "flexion_codo",
        "frames_validos": 10,
        "angulo_maximo_alcanzado": 80.0,
        "repeticiones_estimadas": 1,
        "porcentaje_dentro_rango": 50.0,
    }
    export_rehab_sessions([base], profile, path)
    export_rehab_sessions([{**base, "session_id": "S-2", "angulo_maximo_alcanzado": 90.0}], profile, path)

    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[-1]["comparacion_sesion_anterior"].startswith("Cambio de +10.00")
    assert rows[-1]["nombre_paciente"] == "Paciente de prueba"
    assert rows[-1]["observaciones_paciente"] == "Perfil demo sin datos reales"
