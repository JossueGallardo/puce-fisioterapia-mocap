import sys

from puce_mocap.main_menu import comando_modulo, ejecutar_modulo, ejecutar_pytest, verificar_entorno


class ProcesoFalso:
    def __init__(self, returncode=0):
        self.returncode = returncode


def test_comando_modulo_usa_python_actual():
    assert comando_modulo("2") == [sys.executable, "-m", "puce_mocap.modulo_rehabilitacion_app"]


def test_ejecutar_modulo_mantiene_compatibilidad():
    llamadas = []

    def runner(comando, **kwargs):
        llamadas.append((comando, kwargs))
        return ProcesoFalso(0)

    assert ejecutar_modulo("1", runner=runner) == 0
    assert llamadas[0][0][-1] == "puce_mocap.modulo_pesas_app"


def test_verificar_entorno_incluye_qt_y_pose():
    resultados = verificar_entorno()
    assert resultados["OpenCV"][0]
    assert resultados["cv2.aruco"][0]
    assert resultados["MediaPipe"][0]
    assert resultados["PySide6"][0]


def test_ejecutar_pytest_captura_salida_para_interfaz():
    def runner(_comando, **kwargs):
        assert kwargs["capture_output"] is True
        return type("Proceso", (), {"returncode": 0, "stdout": "70 passed in 1.00s", "stderr": ""})()

    codigo, resumen = ejecutar_pytest(runner=runner)
    assert codigo == 0
    assert "70 passed" in resumen
