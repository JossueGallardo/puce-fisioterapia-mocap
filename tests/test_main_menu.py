import sys

from puce_mocap.main_menu import (
    EstadoMenu,
    MenuPrincipalDashboard,
    comando_modulo,
    ejecutar_modulo,
    ejecutar_pytest,
    verificar_entorno,
)


class ProcesoFalso:
    def __init__(self, returncode=0):
        self.returncode = returncode


def test_comando_modulo_usa_python_actual():
    comando = comando_modulo("2")

    assert comando == [sys.executable, "-m", "puce_mocap.modulo_rehabilitacion_app"]


def test_ejecutar_modulo_delega_en_subprocess_sin_cerrar_menu():
    llamadas = []

    def runner(comando, **kwargs):
        llamadas.append((comando, kwargs))
        return ProcesoFalso(0)

    codigo = ejecutar_modulo("1", runner=runner)

    assert codigo == 0
    assert llamadas[0][0][-1] == "puce_mocap.modulo_pesas_app"
    assert llamadas[0][1]["check"] is False


def test_dashboard_renderiza_menu_y_detecta_clicks():
    dashboard = MenuPrincipalDashboard(ancho=1600, alto=900)
    lienzo = dashboard.render(EstadoMenu())

    assert lienzo.shape == (900, 1600, 3)
    x1, y1, x2, y2 = dashboard.hitboxes_menu["1"]
    assert dashboard.hit_test((x1 + x2) // 2, (y1 + y2) // 2) == "1"


def test_verificar_entorno_no_pide_entrada():
    resultados = verificar_entorno()

    assert resultados["OpenCV"][0]
    assert resultados["cv2.aruco"][0]
    assert resultados["MediaPipe"][0]


def test_ejecutar_pytest_captura_salida_para_interfaz():
    def runner(_comando, **kwargs):
        assert kwargs["capture_output"] is True
        return type("Proceso", (), {"returncode": 0, "stdout": "53 passed in 1.00s", "stderr": ""})()

    codigo, resumen = ejecutar_pytest(runner=runner)

    assert codigo == 0
    assert "53 passed" in resumen
