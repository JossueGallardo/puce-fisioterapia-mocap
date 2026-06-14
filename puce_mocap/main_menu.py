"""Menu principal grafico para orquestar los modulos PUCE."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import sys
from typing import Callable

import cv2
import numpy as np

from puce_mocap.modulo_pesas_app import (
    ALTO_DASHBOARD,
    ANCHO_DASHBOARD,
    ASSETS_DIR,
    COLOR_AZUL,
    COLOR_BORDE,
    COLOR_CYAN,
    COLOR_ROJO_UI,
    COLOR_TARJETA,
    COLOR_TARJETA_SUAVE,
    COLOR_TEXTO,
    COLOR_TEXTO_MUTED,
    COLOR_TEXTO_SUAVE,
    COLOR_VERDE,
    _cargar_logo,
    _cargar_logo_fe_alegria,
    _crear_fondo,
    _dibujar_check,
    _dibujar_icono_barra,
    _dibujar_icono_chart,
    _dibujar_icono_modulo,
    _dibujar_icono_power,
    _dibujar_icono_refresh,
    _dibujar_icono_target,
    _dibujar_rectangulo_redondeado,
    _dibujar_tarjeta_base,
    _dibujar_texto,
    _dibujar_texto_centrado,
    _dibujar_x,
    _superponer_imagen,
    limitar_lineas_texto,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
VENTANA_TITULO = "PUCE MoCap Fisioterapia - Menú Principal"
COLOR_AMARILLO = (45, 205, 245)


@dataclass(frozen=True)
class OpcionMenu:
    clave: str
    titulo: str
    detalle: str
    modulo: str | None
    color: tuple[int, int, int]
    icono: str


OPCIONES: dict[str, OpcionMenu] = {
    "1": OpcionMenu(
        "1",
        "Módulo 1 - Ejercicios con pesas",
        "Sentadilla, press de hombro y peso muerto con retroalimentación en vivo.",
        "puce_mocap.modulo_pesas_app",
        COLOR_CYAN,
        "pesas",
    ),
    "2": OpcionMenu(
        "2",
        "Módulo 2 - Rehabilitación",
        "Perfiles ficticios, rangos configurables y seis ejercicios terapéuticos.",
        "puce_mocap.modulo_rehabilitacion_app",
        COLOR_VERDE,
        "rehab",
    ),
    "3": OpcionMenu(
        "3",
        "Módulo 3 - Caminadora",
        "Métricas de marcha, simetría, longitud de paso y semáforo de alertas.",
        "puce_mocap.modulo_caminadora_app",
        COLOR_AMARILLO,
        "marcha",
    ),
    "4": OpcionMenu(
        "4",
        "FreeMoCap original",
        "Abrir la aplicación base de captura de movimiento sin modificar su núcleo.",
        "freemocap",
        COLOR_AZUL,
        "freemocap",
    ),
    "5": OpcionMenu(
        "5",
        "Verificar entorno",
        "Comprobar OpenCV, ArUco, MediaPipe y ejecutar las pruebas automáticas.",
        None,
        COLOR_CYAN,
        "verificar",
    ),
    "6": OpcionMenu(
        "6",
        "Salir del sistema",
        "Cerrar el menú principal de PUCE MoCap de forma segura.",
        None,
        COLOR_ROJO_UI,
        "salir",
    ),
}

# Compatibilidad con integraciones y pruebas anteriores.
MODULOS = {clave: (opcion.titulo, opcion.modulo) for clave, opcion in OPCIONES.items() if opcion.modulo}


@dataclass
class EstadoMenu:
    seleccion: str = "1"
    hover: str | None = None
    accion_pendiente: str | None = None
    vista: str = "menu"
    mensaje: str = "Sistema listo. Seleccione una opción."
    resultados_entorno: dict[str, tuple[bool, str]] = field(default_factory=dict)
    resultado_pytest: str = "Pruebas automáticas no ejecutadas en esta sesión."


def comando_modulo(opcion: str) -> list[str]:
    """Construye el comando usando el mismo Python del menu."""
    if opcion not in MODULOS:
        raise ValueError(f"Opcion de modulo no valida: {opcion}.")
    return [sys.executable, "-m", str(MODULOS[opcion][1])]


def ejecutar_modulo(
    opcion: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> int:
    """Ejecuta un modulo aislado y devuelve su codigo de salida."""
    try:
        proceso = runner(comando_modulo(opcion), cwd=REPO_ROOT, check=False)
    except OSError:
        return 1
    return int(getattr(proceso, "returncode", 0))


def verificar_entorno() -> dict[str, tuple[bool, str]]:
    """Verifica dependencias clave sin abrir camara ni usar consola interactiva."""
    resultados: dict[str, tuple[bool, str]] = {
        "OpenCV": (False, "No disponible"),
        "cv2.aruco": (False, "No disponible"),
        "MediaPipe": (False, "No disponible"),
        "pose_landmark_cpu.binarypb": (False, "No disponible"),
    }
    try:
        import cv2 as cv2_entorno

        resultados["OpenCV"] = (True, f"Versión {cv2_entorno.__version__}")
        aruco = hasattr(cv2_entorno, "aruco")
        resultados["cv2.aruco"] = (aruco, "Disponible" if aruco else "No disponible")
    except ImportError as exc:
        resultados["OpenCV"] = (False, str(exc))

    try:
        import mediapipe as mp

        resultados["MediaPipe"] = (True, f"Versión {getattr(mp, '__version__', 'disponible')}")
        ruta = Path(mp.__file__).parent / "modules" / "pose_landmark" / "pose_landmark_cpu.binarypb"
        resultados["pose_landmark_cpu.binarypb"] = (ruta.exists(), "Archivo encontrado" if ruta.exists() else "Falta archivo")
    except ImportError as exc:
        resultados["MediaPipe"] = (False, str(exc))
    return resultados


def ejecutar_pytest(
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> tuple[int, str]:
    """Ejecuta pytest y devuelve un resumen breve para la interfaz."""
    try:
        proceso = runner(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return 1, f"No se pudo ejecutar pytest: {exc}"

    salida = f"{getattr(proceso, 'stdout', '')}\n{getattr(proceso, 'stderr', '')}".strip()
    resumen = next((linea.strip() for linea in reversed(salida.splitlines()) if "passed" in linea or "failed" in linea), "")
    codigo = int(getattr(proceso, "returncode", 0))
    if not resumen:
        resumen = "Pruebas completadas correctamente." if codigo == 0 else "Las pruebas finalizaron con errores."
    return codigo, resumen


class MenuPrincipalDashboard:
    """Renderer y mapa de interacción del menú gráfico."""

    def __init__(self, ancho: int = ANCHO_DASHBOARD, alto: int = ALTO_DASHBOARD):
        self.ancho = ancho
        self.alto = alto
        self.logo_puce = _cargar_logo(ASSETS_DIR / "logo_puce.png", 335, 92)
        self.logo_fe_alegria = _cargar_logo_fe_alegria(ASSETS_DIR / "logo_fe_alegria.png", 110, 104)
        self.hitboxes_menu = self._crear_hitboxes_menu()
        self.hitboxes_verificacion = {
            "pytest": (610, 746, 960, 812),
            "volver": (990, 746, 1340, 812),
        }

    @staticmethod
    def _crear_hitboxes_menu() -> dict[str, tuple[int, int, int, int]]:
        hitboxes = {}
        ancho = 492
        alto = 250
        for indice, clave in enumerate(OPCIONES):
            fila, columna = divmod(indice, 3)
            x = 24 + columna * 518
            y = 174 + fila * 274
            hitboxes[clave] = (x, y, x + ancho, y + alto)
        return hitboxes

    @staticmethod
    def _contiene(rectangulo: tuple[int, int, int, int], x: int, y: int) -> bool:
        x1, y1, x2, y2 = rectangulo
        return x1 <= x <= x2 and y1 <= y <= y2

    def hit_test(self, x: int, y: int, vista: str = "menu") -> str | None:
        hitboxes = self.hitboxes_menu if vista == "menu" else self.hitboxes_verificacion
        return next((clave for clave, rectangulo in hitboxes.items() if self._contiene(rectangulo, x, y)), None)

    def render(self, estado: EstadoMenu) -> np.ndarray:
        lienzo = _crear_fondo(self.ancho, self.alto)
        self._dibujar_header(lienzo)
        if estado.vista == "verificacion":
            self._dibujar_verificacion(lienzo, estado)
        else:
            self._dibujar_opciones(lienzo, estado)
        self._dibujar_footer(lienzo, estado.mensaje)
        return lienzo

    def _dibujar_header(self, lienzo: np.ndarray) -> None:
        if self.logo_puce is not None:
            _superponer_imagen(lienzo, self.logo_puce, 38, 48)
        else:
            _dibujar_texto(lienzo, "Pontificia Universidad Católica del Ecuador", 38, 92, 0.50, COLOR_CYAN, 2)

        _dibujar_texto_centrado(lienzo, "PUCE MoCap Fisioterapia", self.ancho // 2, 82, 1.18, COLOR_TEXTO, 2)
        _dibujar_texto_centrado(
            lienzo,
            "Menú principal integrado | Vinculación con la Comunidad",
            self.ancho // 2,
            122,
            0.57,
            COLOR_TEXTO_SUAVE,
            1,
        )
        if self.logo_fe_alegria is not None:
            _superponer_imagen(lienzo, self.logo_fe_alegria, self.ancho - 292, 44)
        _dibujar_texto(lienzo, "Fe y Alegría", self.ancho - 178, 87, 0.68, COLOR_TEXTO, 2)
        _dibujar_texto(lienzo, "Ecuador", self.ancho - 178, 120, 0.68, COLOR_TEXTO, 2)

    def _dibujar_opciones(self, lienzo: np.ndarray, estado: EstadoMenu) -> None:
        for clave, opcion in OPCIONES.items():
            x1, y1, x2, y2 = self.hitboxes_menu[clave]
            seleccionado = clave == estado.seleccion
            hover = clave == estado.hover
            relleno = (48, 43, 28) if seleccionado else COLOR_TARJETA
            if hover and not seleccionado:
                relleno = COLOR_TARJETA_SUAVE
            _dibujar_rectangulo_redondeado(lienzo, x1, y1, x2 - x1, y2 - y1, 16, relleno, -1)
            _dibujar_rectangulo_redondeado(
                lienzo,
                x1,
                y1,
                x2 - x1,
                y2 - y1,
                16,
                opcion.color if seleccionado or hover else COLOR_BORDE,
                3 if seleccionado else 1,
            )
            cv2.circle(lienzo, (x1 + 64, y1 + 65), 35, (45, 45, 35), -1, cv2.LINE_AA)
            cv2.circle(lienzo, (x1 + 64, y1 + 65), 35, opcion.color, 2, cv2.LINE_AA)
            self._dibujar_icono(lienzo, opcion.icono, x1 + 43, y1 + 42, opcion.color)
            _dibujar_texto(lienzo, opcion.titulo, x1 + 118, y1 + 62, 0.62, COLOR_TEXTO, 2)

            lineas = limitar_lineas_texto(opcion.detalle, x2 - x1 - 76, 0.47, 1, 3)
            for indice, linea in enumerate(lineas):
                _dibujar_texto(lienzo, linea, x1 + 38, y1 + 130 + indice * 29, 0.47, COLOR_TEXTO_SUAVE, 1)

            etiqueta = "ABRIR" if opcion.modulo else ("REVISAR" if clave == "5" else "CERRAR")
            _dibujar_rectangulo_redondeado(lienzo, x1 + 340, y2 - 54, 116, 32, 7, (45, 43, 34), -1)
            _dibujar_texto_centrado(lienzo, etiqueta, x1 + 398, y2 - 31, 0.38, opcion.color, 2)

    @staticmethod
    def _dibujar_icono(
        lienzo: np.ndarray, nombre: str, x: int, y: int, color: tuple[int, int, int]
    ) -> None:
        if nombre == "pesas":
            _dibujar_icono_barra(lienzo, x, y, color)
        elif nombre == "rehab":
            _dibujar_icono_target(lienzo, x, y, color)
        elif nombre == "marcha":
            _dibujar_icono_chart(lienzo, x, y, color)
        elif nombre == "freemocap":
            _dibujar_icono_modulo(lienzo, x, y, color)
        elif nombre == "verificar":
            _dibujar_icono_refresh(lienzo, x, y, color)
        else:
            _dibujar_icono_power(lienzo, x, y, color)

    def _dibujar_verificacion(self, lienzo: np.ndarray, estado: EstadoMenu) -> None:
        _dibujar_texto(lienzo, "Verificación rápida del entorno", 42, 188, 0.82, COLOR_TEXTO, 2)
        _dibujar_texto(
            lienzo,
            "Comprobación local sin abrir cámaras ni modificar dependencias.",
            42,
            224,
            0.48,
            COLOR_TEXTO_SUAVE,
            1,
        )

        for indice, (nombre, (correcto, detalle)) in enumerate(estado.resultados_entorno.items()):
            fila, columna = divmod(indice, 2)
            x = 42 + columna * 765
            y = 260 + fila * 170
            color = COLOR_VERDE if correcto else COLOR_ROJO_UI
            _dibujar_tarjeta_base(lienzo, x, y, 730, 145, 14)
            if correcto:
                _dibujar_check(lienzo, (x + 58, y + 70), 24, color)
            else:
                _dibujar_x(lienzo, (x + 58, y + 70), 24, color)
            _dibujar_texto(lienzo, nombre, x + 105, y + 58, 0.58, COLOR_TEXTO, 2)
            _dibujar_texto(lienzo, detalle, x + 105, y + 94, 0.44, color, 1)

        _dibujar_tarjeta_base(lienzo, 42, 610, 1492, 104, 14)
        _dibujar_icono_chart(lienzo, 66, 632, COLOR_CYAN)
        _dibujar_texto(lienzo, "PRUEBAS AUTOMÁTICAS", 116, 652, 0.42, COLOR_TEXTO_SUAVE, 2)
        for indice, linea in enumerate(limitar_lineas_texto(estado.resultado_pytest, 1330, 0.49, 1, 2)):
            _dibujar_texto(lienzo, linea, 116, 684 + indice * 25, 0.49, COLOR_TEXTO, 1)

        self._dibujar_boton_accion(lienzo, self.hitboxes_verificacion["pytest"], "Ejecutar pytest", COLOR_VERDE, True)
        self._dibujar_boton_accion(lienzo, self.hitboxes_verificacion["volver"], "Volver al menú", COLOR_AZUL, False)

    @staticmethod
    def _dibujar_boton_accion(
        lienzo: np.ndarray,
        rectangulo: tuple[int, int, int, int],
        texto: str,
        color: tuple[int, int, int],
        pytest: bool,
    ) -> None:
        x1, y1, x2, y2 = rectangulo
        _dibujar_rectangulo_redondeado(lienzo, x1, y1, x2 - x1, y2 - y1, 10, (42, 38, 31), -1)
        _dibujar_rectangulo_redondeado(lienzo, x1, y1, x2 - x1, y2 - y1, 10, color, 2)
        if pytest:
            _dibujar_icono_refresh(lienzo, x1 + 28, y1 + 12, color)
        else:
            cv2.arrowedLine(lienzo, (x1 + 70, y1 + 34), (x1 + 34, y1 + 34), color, 3, cv2.LINE_AA, tipLength=0.35)
        _dibujar_texto_centrado(lienzo, texto, (x1 + x2) // 2 + 20, y1 + 43, 0.54, COLOR_TEXTO, 2)

    def _dibujar_footer(self, lienzo: np.ndarray, mensaje: str) -> None:
        _dibujar_tarjeta_base(lienzo, 24, 846, 1552, 40, 10)
        cv2.circle(lienzo, (50, 866), 6, COLOR_VERDE, -1, cv2.LINE_AA)
        _dibujar_texto(lienzo, mensaje, 70, 873, 0.43, COLOR_TEXTO_SUAVE, 1)
        _dibujar_texto(
            lienzo,
            "Basado en FreeMoCap | Jon Matthis y equipo FreeMoCap | AGPLv3",
            1065,
            873,
            0.37,
            COLOR_TEXTO_MUTED,
            1,
        )


def _crear_ventana(dashboard: MenuPrincipalDashboard, estado: EstadoMenu) -> None:
    cv2.namedWindow(VENTANA_TITULO, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(VENTANA_TITULO, dashboard.ancho, dashboard.alto)

    def manejar_mouse(evento: int, x: int, y: int, _flags: int, _param) -> None:
        vista = estado.vista
        if evento == cv2.EVENT_MOUSEMOVE:
            estado.hover = dashboard.hit_test(x, y, vista)
            if vista == "menu" and estado.hover in OPCIONES:
                estado.seleccion = estado.hover
        elif evento == cv2.EVENT_LBUTTONUP:
            accion = dashboard.hit_test(x, y, vista)
            if accion is not None:
                estado.accion_pendiente = accion

    cv2.setMouseCallback(VENTANA_TITULO, manejar_mouse)


def _accion_teclado(tecla: int, estado: EstadoMenu) -> str | None:
    if estado.vista == "verificacion":
        if tecla in (27, ord("q"), ord("v")):
            return "volver"
        if tecla in (13, ord("p")):
            return "pytest"
        return None

    if tecla in tuple(ord(clave) for clave in OPCIONES):
        return chr(tecla)
    claves = list(OPCIONES)
    indice = claves.index(estado.seleccion)
    if tecla in (81, 2424832):
        estado.seleccion = claves[(indice - 1) % len(claves)]
    elif tecla in (83, 2555904):
        estado.seleccion = claves[(indice + 1) % len(claves)]
    elif tecla in (82, 2490368):
        estado.seleccion = claves[(indice - 3) % len(claves)]
    elif tecla in (84, 2621440):
        estado.seleccion = claves[(indice + 3) % len(claves)]
    elif tecla == 13:
        return estado.seleccion
    elif tecla in (27, ord("q")):
        return "6"
    return None


def main() -> None:
    """Ejecuta el menú gráfico y recupera el control al cerrar cada módulo."""
    dashboard = MenuPrincipalDashboard()
    estado = EstadoMenu()
    _crear_ventana(dashboard, estado)

    while True:
        cv2.imshow(VENTANA_TITULO, dashboard.render(estado))
        tecla = cv2.waitKeyEx(30)
        accion = estado.accion_pendiente or _accion_teclado(tecla, estado)
        estado.accion_pendiente = None

        if accion in MODULOS:
            nombre = MODULOS[accion][0]
            estado.mensaje = f"Abriendo {nombre}..."
            cv2.imshow(VENTANA_TITULO, dashboard.render(estado))
            cv2.waitKey(60)
            cv2.destroyWindow(VENTANA_TITULO)
            codigo = ejecutar_modulo(accion)
            estado.mensaje = (
                f"{nombre} cerrado. Menú listo."
                if codigo == 0
                else f"{nombre} terminó con código {codigo}. Puede intentar nuevamente."
            )
            _crear_ventana(dashboard, estado)
        elif accion == "5":
            estado.resultados_entorno = verificar_entorno()
            estado.resultado_pytest = "Pruebas automáticas no ejecutadas en esta sesión."
            estado.vista = "verificacion"
            estado.hover = None
            estado.mensaje = "Verificación del entorno completada."
        elif accion == "pytest":
            estado.resultado_pytest = "Ejecutando pruebas automáticas..."
            cv2.imshow(VENTANA_TITULO, dashboard.render(estado))
            cv2.waitKey(60)
            codigo, resumen = ejecutar_pytest()
            estado.resultado_pytest = resumen
            estado.mensaje = "pytest finalizó correctamente." if codigo == 0 else "pytest encontró errores para revisar."
        elif accion == "volver":
            estado.vista = "menu"
            estado.hover = None
            estado.mensaje = "Sistema listo. Seleccione una opción."
        elif accion == "6":
            break

        try:
            if cv2.getWindowProperty(VENTANA_TITULO, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
