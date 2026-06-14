from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from puce_mocap.rehab_analyzer import evaluar_ejercicio_rehabilitacion
from puce_mocap.rehab_profiles import cargar_perfil_paciente
from puce_mocap.rehab_report import generar_reporte_rehabilitacion_csv
from puce_mocap.rehab_session import RehabSession


def esqueleto_codo_90_grados():
    return {
        "right_shoulder": [1.0, 0.0, 0.0],
        "right_elbow": [0.0, 0.0, 0.0],
        "right_wrist": [0.0, 1.0, 0.0],
    }


def esqueleto_codo_extendido():
    return {
        "right_shoulder": [-1.0, 0.0, 0.0],
        "right_elbow": [0.0, 0.0, 0.0],
        "right_wrist": [1.0, 0.0, 0.0],
    }


def imprimir_resultado(titulo, resultado):
    print(f"\n{titulo}")
    print(f"Estado: {resultado.estado} ({resultado.color})")
    print(f"Angulo actual: {resultado.angulo_actual if resultado.angulo_actual is not None else 'N/D'}")
    print(f"Rango objetivo: {resultado.angulo_minimo:.0f}-{resultado.angulo_maximo:.0f} grados")
    for mensaje in resultado.mensajes:
        print(f"  - {mensaje}")


def main():
    perfil = cargar_perfil_paciente(REPO_ROOT / "profiles" / "paciente_demo.json")
    dentro = evaluar_ejercicio_rehabilitacion("flexion_codo", esqueleto_codo_90_grados(), perfil)
    fuera = evaluar_ejercicio_rehabilitacion("flexion_codo", esqueleto_codo_extendido(), perfil)
    incompleto = evaluar_ejercicio_rehabilitacion("flexion_codo", {}, perfil)

    print("PUCE MoCap - Semana 5 / Modulo de Rehabilitacion")
    print(f"Perfil ficticio: {perfil['codigo_paciente']} - {perfil['nombre']}")
    imprimir_resultado("Caso dentro del rango", dentro)
    imprimir_resultado("Caso fuera del rango", fuera)
    imprimir_resultado("Caso con postura incompleta", incompleto)

    sesion = RehabSession("flexion_codo", perfil["codigo_paciente"])
    for resultado in (fuera, dentro, dentro, incompleto):
        sesion.registrar_resultado(resultado)

    resumen = sesion.exportar_resumen()
    print("\nResumen de sesion ficticia")
    print(f"Frames validos: {resumen['frames_validos']} / {resumen['total_frames']}")
    print(f"Porcentaje dentro del rango: {resumen['porcentaje_dentro_rango']:.2f}%")
    print(f"Angulo maximo alcanzado: {resumen['angulo_maximo_alcanzado']}")
    print(f"Repeticiones estimadas: {resumen['repeticiones_estimadas']}")

    ruta = generar_reporte_rehabilitacion_csv(
        resumen,
        perfil,
        REPO_ROOT / "reports" / "semana_5_rehab_report.csv",
    )
    print(f"Reporte CSV generado: {ruta}")


if __name__ == "__main__":
    main()
