"""Aplicacion final de Semana 4 / Modulo 3: analisis de marcha en caminadora."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Mapping, Sequence

import cv2
import numpy as np

from puce_mocap.gait_analyzer import (
    COLOR_AMARILLO,
    COLOR_ROJO as COLOR_ROJO_LOGICO,
    COLOR_VERDE as COLOR_VERDE_LOGICO,
    ESTADO_ATENCION,
    ESTADO_NORMAL,
    ESTADO_REVISAR,
    GaitAnalysisResult,
    MENSAJE_POSTURA_INCOMPLETA,
    analizar_marcha,
)
from puce_mocap.gait_report import generar_reporte_marcha_csv
from puce_mocap.gait_session import GaitSession
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
    REPO_ROOT,
    _cargar_logo,
    _cargar_logo_fe_alegria,
    _crear_fondo,
    _dibujar_barra,
    _dibujar_check,
    _dibujar_icono_chart,
    _dibujar_icono_power,
    _dibujar_icono_refresh,
    _dibujar_rectangulo_redondeado,
    _dibujar_tarjeta_base,
    _dibujar_texto,
    _dibujar_texto_centrado,
    _dibujar_x,
    _medir_texto,
    _pegar_imagen_redondeada,
    _superponer_imagen,
    formatear_duracion,
    limitar_lineas_texto,
)

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - se valida manualmente en Windows
    mp = None


VENTANA_TITULO = "PUCE MoCap - Modulo de Caminadora"
SUBTITULO = "Analisis de marcha | Basado en FreeMoCap | MediaPipe Pose como complemento en vivo"
REPORTE_CAMINADORA_PATH = REPO_ROOT / "reports" / "semana_4_gait_report.csv"
MENSAJE_UNA_CAMARA = "Modo una camara: metricas aproximadas. Para analisis completo usar 2-3 camaras calibradas."
COLOR_AMARILLO_UI = (45, 205, 245)

LANDMARKS_REQUERIDOS = (
    "nose",
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


@dataclass
class EstadoAppCaminadora:
    """Estado visual y de sesion de la app live."""

    sesion: GaitSession
    sesion_activa: bool = False
    inicio_sesion: float = 0.0
    vista: str = "LATERAL"
    reporte_generado: bool = False
    duracion_final: float | None = None


def _punto_landmark(landmarks, landmark_id: int, min_visibility: float = 0.35) -> list[float] | None:
    landmark = landmarks[landmark_id]
    if getattr(landmark, "visibility", 1.0) < min_visibility:
        return None
    return [float(landmark.x), float(-landmark.y), float(-landmark.z)]


def mediapipe_a_esqueleto_marcha(pose_landmarks) -> dict[str, list[float]]:
    """Convierte landmarks de MediaPipe Pose al formato de gait_analyzer."""
    if mp is None:  # pragma: no cover
        return {}

    mp_pose = mp.solutions.pose
    landmarks = pose_landmarks.landmark
    mapa = {
        "nose": mp_pose.PoseLandmark.NOSE.value,
        "head": mp_pose.PoseLandmark.NOSE.value,
        "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
        "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER.value,
        "right_hip": mp_pose.PoseLandmark.RIGHT_HIP.value,
        "left_hip": mp_pose.PoseLandmark.LEFT_HIP.value,
        "right_knee": mp_pose.PoseLandmark.RIGHT_KNEE.value,
        "left_knee": mp_pose.PoseLandmark.LEFT_KNEE.value,
        "right_ankle": mp_pose.PoseLandmark.RIGHT_ANKLE.value,
        "left_ankle": mp_pose.PoseLandmark.LEFT_ANKLE.value,
        "right_foot_index": mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value,
        "left_foot_index": mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value,
    }

    esqueleto = {}
    for nombre, landmark_id in mapa.items():
        punto = _punto_landmark(landmarks, landmark_id)
        if punto is not None:
            esqueleto[nombre] = punto
    return esqueleto


def postura_completa(esqueleto: Mapping[str, Sequence[float]]) -> bool:
    """Valida landmarks minimos antes de registrar frames validos."""
    return all(nombre in esqueleto for nombre in LANDMARKS_REQUERIDOS)


def feedback_incompleto() -> GaitAnalysisResult:
    return GaitAnalysisResult(
        estado=ESTADO_REVISAR,
        color=COLOR_ROJO_LOGICO,
        metricas={
            "inclinacion_tronco": None,
            "angulo_rodilla_derecha": None,
            "angulo_rodilla_izquierda": None,
            "asimetria_rodillas": None,
            "longitud_paso": None,
            "oscilacion_lateral_cadera": None,
        },
        mensajes=[MENSAJE_POSTURA_INCOMPLETA],
        frame_valido=False,
    )


def _color_estado(resultado: GaitAnalysisResult) -> tuple[int, int, int]:
    if resultado.color == COLOR_VERDE_LOGICO:
        return COLOR_VERDE
    if resultado.color == COLOR_AMARILLO:
        return COLOR_AMARILLO_UI
    return COLOR_ROJO_UI


def _label_estado(resultado: GaitAnalysisResult) -> str:
    if resultado.estado == ESTADO_NORMAL:
        return "VERDE / NORMAL"
    if resultado.estado == ESTADO_ATENCION:
        return "AMARILLO / ATENCION"
    return "ROJO / REVISAR"


def _valor(valor: float | None, unidad: str = "", decimales: int = 1) -> str:
    if valor is None:
        return "N/D"
    return f"{valor:.{decimales}f}{unidad}"


class ModuloCaminadoraDashboard:
    """Renderer OpenCV para el dashboard de caminadora."""

    def __init__(self, ancho: int = ANCHO_DASHBOARD, alto: int = ALTO_DASHBOARD, assets_dir: Path = ASSETS_DIR):
        self.ancho = ancho
        self.alto = alto
        self.logo_puce = _cargar_logo(assets_dir / "logo_puce.png", 335, 92)
        self.logo_fe_alegria = _cargar_logo_fe_alegria(assets_dir / "logo_fe_alegria.png", 110, 104)
        self._bases: dict[str, np.ndarray] = {}

    def render(
        self,
        frame_camara: np.ndarray,
        resultado: GaitAnalysisResult,
        estado_app: EstadoAppCaminadora,
        historial: Sequence[float],
    ) -> np.ndarray:
        lienzo = self._obtener_base(estado_app.vista).copy()
        self._dibujar_camara(lienzo, frame_camara)
        self._dibujar_metricas(lienzo, resultado)
        self._dibujar_grafica(lienzo, historial)
        self._dibujar_sesion(lienzo, estado_app)
        return lienzo

    def _obtener_base(self, vista: str) -> np.ndarray:
        if vista not in self._bases:
            lienzo = _crear_fondo(self.ancho, self.alto)
            self._dibujar_header(lienzo)
            self._dibujar_base_camara(lienzo)
            self._dibujar_base_metricas(lienzo)
            self._dibujar_panel_controles(lienzo, vista)
            self._dibujar_base_grafica(lienzo)
            self._dibujar_base_sesion(lienzo)
            self._bases[vista] = lienzo
        return self._bases[vista]

    def _dibujar_header(self, lienzo: np.ndarray) -> None:
        if self.logo_puce is not None:
            _superponer_imagen(lienzo, self.logo_puce, 38, 52)
        else:
            _dibujar_texto(lienzo, "Pontificia Universidad", 40, 82, 0.62, COLOR_CYAN, 2)
            _dibujar_texto(lienzo, "Catolica del Ecuador", 40, 111, 0.62, COLOR_CYAN, 2)

        _dibujar_texto_centrado(lienzo, "PUCE MoCap - Modulo de Caminadora", self.ancho // 2, 91, 1.05, COLOR_TEXTO, 2)
        _dibujar_texto_centrado(lienzo, SUBTITULO, self.ancho // 2, 128, 0.50, COLOR_TEXTO_SUAVE, 1)

        if self.logo_fe_alegria is not None:
            _superponer_imagen(lienzo, self.logo_fe_alegria, self.ancho - 292, 48)
        _dibujar_texto(lienzo, "Fe y Alegria", self.ancho - 178, 91, 0.68, COLOR_TEXTO, 2)
        _dibujar_texto(lienzo, "Ecuador", self.ancho - 178, 124, 0.68, COLOR_TEXTO, 2)

    def _dibujar_base_camara(self, lienzo: np.ndarray) -> None:
        _dibujar_tarjeta_base(lienzo, 24, 156, 770, 520, 18)

    def _dibujar_camara(self, lienzo: np.ndarray, frame_camara: np.ndarray) -> None:
        x, y, w, h = 24, 156, 770, 520
        _pegar_imagen_redondeada(lienzo, frame_camara, x + 14, y + 14, w - 28, h - 28, 14)
        _dibujar_rectangulo_redondeado(lienzo, x + 14, y + 14, w - 28, h - 28, 14, (55, 57, 45), 1)
        _dibujar_rectangulo_redondeado(lienzo, x + 24, y + 26, 105, 34, 15, (36, 37, 38), -1)
        cv2.circle(lienzo, (x + 45, y + 43), 6, COLOR_VERDE, -1, cv2.LINE_AA)
        _dibujar_texto(lienzo, "EN VIVO", x + 61, y + 51, 0.42, COLOR_TEXTO, 2)

    def _dibujar_base_metricas(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 815, 156, 440, 405
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        cv2.circle(lienzo, (x + 43, y + 41), 23, (92, 78, 16), -1, cv2.LINE_AA)
        _dibujar_icono_chart(lienzo, x + 24, y + 19, COLOR_CYAN)
        _dibujar_texto(lienzo, "METRICAS DE MARCHA", x + 76, y + 39, 0.40, COLOR_TEXTO_SUAVE, 2)
        _dibujar_texto(lienzo, MENSAJE_UNA_CAMARA, x + 32, y + 380, 0.33, COLOR_TEXTO_MUTED, 1)

    def _dibujar_metricas(self, lienzo: np.ndarray, resultado: GaitAnalysisResult) -> None:
        x, y = 815, 156
        metricas = resultado.metricas
        filas = [
            ("Inclinacion tronco", _valor(metricas.get("inclinacion_tronco"), " deg")),
            ("Rodilla derecha", _valor(metricas.get("angulo_rodilla_derecha"), " deg")),
            ("Rodilla izquierda", _valor(metricas.get("angulo_rodilla_izquierda"), " deg")),
            ("Asimetria rodillas", _valor(metricas.get("asimetria_rodillas"), " deg")),
            ("Longitud paso", _valor(metricas.get("longitud_paso"), "", 2)),
        ]

        for indice, (titulo, valor) in enumerate(filas):
            fila_y = y + 78 + indice * 47
            _dibujar_texto(lienzo, titulo, x + 34, fila_y, 0.42, COLOR_TEXTO_SUAVE, 1)
            _dibujar_texto(lienzo, valor, x + 285, fila_y, 0.50, COLOR_TEXTO, 2)

        color = _color_estado(resultado)
        fondo = (42, 102, 43) if resultado.estado == ESTADO_NORMAL else (72, 79, 34) if resultado.estado == ESTADO_ATENCION else (48, 35, 82)
        chip_x, chip_y, chip_w, chip_h = x + 34, y + 306, 372, 52
        _dibujar_rectangulo_redondeado(lienzo, chip_x, chip_y, chip_w, chip_h, 10, fondo, -1)
        _dibujar_rectangulo_redondeado(lienzo, chip_x, chip_y, chip_w, chip_h, 10, color, 1)
        if resultado.estado == ESTADO_NORMAL:
            _dibujar_check(lienzo, (chip_x + 32, chip_y + 26), 15, color)
        else:
            _dibujar_x(lienzo, (chip_x + 32, chip_y + 26), 15, color)
        _dibujar_texto_centrado(lienzo, _label_estado(resultado), chip_x + chip_w // 2 + 12, chip_y + 34, 0.47, COLOR_TEXTO, 2)

        mensaje = resultado.mensajes[0] if resultado.mensajes else "Sesion iniciada."
        for idx, linea in enumerate(limitar_lineas_texto(mensaje, 360, 0.34, 1, 2)):
            _dibujar_texto(lienzo, linea, x + 34, y + 275 + idx * 21, 0.34, COLOR_TEXTO, 1)

    def _dibujar_panel_controles(self, lienzo: np.ndarray, vista: str) -> None:
        x, y, w, h = 1275, 156, 300, 450
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        _dibujar_texto(lienzo, "CONTROLES", x + 34, y + 40, 0.43, COLOR_TEXTO_SUAVE, 2)

        botones = [
            ("i", "Iniciar sesion", COLOR_VERDE),
            ("t", "Terminar sesion", COLOR_AMARILLO_UI),
            ("r", "Reiniciar", COLOR_AZUL),
            ("q", "Salir", COLOR_ROJO_UI),
            ("1", "Vista lateral", COLOR_CYAN if vista == "LATERAL" else COLOR_TEXTO_MUTED),
            ("2", "Vista frontal", COLOR_CYAN if vista == "FRONTAL" else COLOR_TEXTO_MUTED),
        ]
        for indice, (tecla, texto, color) in enumerate(botones):
            boton_y = y + 62 + indice * 61
            _dibujar_rectangulo_redondeado(lienzo, x + 20, boton_y, w - 40, 48, 9, COLOR_TARJETA_SUAVE, -1)
            _dibujar_rectangulo_redondeado(lienzo, x + 20, boton_y, w - 40, 48, 9, color, 1)
            if tecla == "q":
                _dibujar_icono_power(lienzo, x + 35, boton_y + 5, color)
            elif tecla == "r":
                _dibujar_icono_refresh(lienzo, x + 35, boton_y + 5, color)
            else:
                _dibujar_texto_centrado(lienzo, tecla.upper(), x + 55, boton_y + 31, 0.42, color, 2)
            _dibujar_texto(lienzo, texto, x + 88, boton_y + 31, 0.43, COLOR_TEXTO, 2)

    def _dibujar_base_grafica(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 24, 708, 700, 148
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 16)
        _dibujar_texto(lienzo, "CICLO DE MARCHA", x + 34, y + 38, 0.43, COLOR_TEXTO_SUAVE, 2)
        _dibujar_texto(lienzo, "Linea: ultimos angulos de rodilla derecha", x + 34, y + 64, 0.34, COLOR_TEXTO_MUTED, 1)

    def _dibujar_grafica(self, lienzo: np.ndarray, historial: Sequence[float]) -> None:
        x, y, w, h = 24, 708, 700, 148
        gx, gy, gw, gh = x + 34, y + 78, w - 68, 48
        _dibujar_rectangulo_redondeado(lienzo, gx, gy, gw, gh, 8, (24, 22, 18), -1)
        cv2.line(lienzo, (gx, gy + gh // 2), (gx + gw, gy + gh // 2), COLOR_BORDE, 1, cv2.LINE_AA)
        if len(historial) < 2:
            return

        valores = np.asarray(historial, dtype=float)
        minimo = float(np.nanmin(valores))
        maximo = float(np.nanmax(valores))
        if np.isclose(maximo, minimo):
            maximo = minimo + 1.0

        puntos = []
        for indice, valor in enumerate(valores):
            px = gx + int((indice / max(1, len(valores) - 1)) * gw)
            normalizado = (float(valor) - minimo) / (maximo - minimo)
            py = gy + gh - int(normalizado * gh)
            puntos.append((px, py))
        for punto_a, punto_b in zip(puntos, puntos[1:]):
            cv2.line(lienzo, punto_a, punto_b, COLOR_CYAN, 2, cv2.LINE_AA)

    def _dibujar_base_sesion(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 745, 708, 830, 148
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 16)
        _dibujar_texto(lienzo, "SESION DE CAMINADORA", x + 34, y + 38, 0.43, COLOR_TEXTO_SUAVE, 2)
        titulos = ["DURACION", "FRAMES VALIDOS", "VERDE", "AMARILLO", "ROJO"]
        for indice, titulo in enumerate(titulos):
            col_x = x + 34 + indice * 156
            _dibujar_texto(lienzo, titulo, col_x, y + 78, 0.33, COLOR_TEXTO_SUAVE, 1)

    def _dibujar_sesion(self, lienzo: np.ndarray, estado_app: EstadoAppCaminadora) -> None:
        x, y = 745, 708
        sesion = estado_app.sesion
        if estado_app.sesion_activa:
            duracion = time.monotonic() - estado_app.inicio_sesion
        elif estado_app.duracion_final is not None:
            duracion = estado_app.duracion_final
        else:
            duracion = sesion.duracion_segundos
        valores = [
            formatear_duracion(duracion),
            str(sesion.frames_validos),
            f"{sesion.porcentaje_verde:.0f}%",
            f"{sesion.porcentaje_amarillo:.0f}%",
            f"{sesion.porcentaje_rojo:.0f}%",
        ]
        colores = [COLOR_AZUL, COLOR_TEXTO, COLOR_VERDE, COLOR_AMARILLO_UI, COLOR_ROJO_UI]
        for indice, (valor, color) in enumerate(zip(valores, colores)):
            col_x = x + 34 + indice * 156
            _dibujar_texto(lienzo, valor, col_x, y + 110, 0.48, color, 2)
            if indice >= 2:
                progreso = [sesion.porcentaje_verde, sesion.porcentaje_amarillo, sesion.porcentaje_rojo][indice - 2] / 100.0
                _dibujar_barra(lienzo, col_x, y + 124, 112, 8, progreso, color)


def _reiniciar_estado_app() -> EstadoAppCaminadora:
    return EstadoAppCaminadora(sesion=GaitSession(), inicio_sesion=time.monotonic())


def _guardar_reporte(estado_app: EstadoAppCaminadora) -> Path:
    duracion = estado_app.duracion_final
    if duracion is None:
        duracion = time.monotonic() - estado_app.inicio_sesion
    resumen = estado_app.sesion.exportar_resumen(duracion_segundos=duracion)
    ruta = generar_reporte_marcha_csv(resumen, REPORTE_CAMINADORA_PATH)
    estado_app.reporte_generado = True
    return ruta


def main() -> None:
    """Ejecuta la interfaz live de caminadora con una camara."""
    if mp is None:
        print("MediaPipe no esta instalado. Ejecuta: python -m pip install mediapipe")
        return

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    landmark_spec = mp_drawing.DrawingSpec(color=(80, 255, 90), thickness=2, circle_radius=4)
    connection_spec = mp_drawing.DrawingSpec(color=(60, 215, 240), thickness=2, circle_radius=2)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("No se pudo abrir la camara 0. Verifica permisos de camara en Windows.")
        return

    dashboard = ModuloCaminadoraDashboard()
    estado_app = _reiniciar_estado_app()
    historial_rodilla: deque[float] = deque(maxlen=80)
    resultado = feedback_incompleto()

    cv2.namedWindow(VENTANA_TITULO, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(VENTANA_TITULO, dashboard.ancho, dashboard.alto)
    print("PUCE MoCap - Modulo de Caminadora iniciado.")
    print("Teclas: i iniciar | t terminar y reportar | r reiniciar | q salir | 1 lateral | 2 frontal")

    with mp_pose.Pose(model_complexity=1, min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer un frame de la camara.")
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultado_pose = pose.process(rgb)
            frame_visual = frame.copy()

            if resultado_pose.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame_visual,
                    resultado_pose.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=landmark_spec,
                    connection_drawing_spec=connection_spec,
                )
                esqueleto = mediapipe_a_esqueleto_marcha(resultado_pose.pose_landmarks)
                resultado = analizar_marcha(esqueleto) if postura_completa(esqueleto) else feedback_incompleto()
            else:
                resultado = feedback_incompleto()

            angulo_rodilla = resultado.metricas.get("angulo_rodilla_derecha")
            if angulo_rodilla is not None:
                historial_rodilla.append(float(angulo_rodilla))
            if estado_app.sesion_activa and resultado.frame_valido:
                estado_app.sesion.registrar_resultado(resultado)

            lienzo = dashboard.render(frame_visual, resultado, estado_app, list(historial_rodilla))
            cv2.imshow(VENTANA_TITULO, lienzo)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                if estado_app.sesion.frames_validos > 0 and not estado_app.reporte_generado:
                    ruta = _guardar_reporte(estado_app)
                    print(f"Reporte CSV generado: {ruta}")
                break
            if tecla == ord("i"):
                if not estado_app.sesion_activa:
                    if estado_app.sesion.frames_validos == 0:
                        estado_app.sesion = GaitSession()
                    estado_app.sesion_activa = True
                    estado_app.inicio_sesion = time.monotonic()
                    estado_app.reporte_generado = False
                    estado_app.duracion_final = None
            elif tecla == ord("t"):
                if estado_app.sesion_activa:
                    estado_app.duracion_final = time.monotonic() - estado_app.inicio_sesion
                estado_app.sesion_activa = False
                ruta = _guardar_reporte(estado_app)
                print(f"Reporte CSV generado: {ruta}")
            elif tecla == ord("r"):
                estado_app = _reiniciar_estado_app()
                historial_rodilla.clear()
            elif tecla == ord("1"):
                estado_app.vista = "LATERAL"
            elif tecla == ord("2"):
                estado_app.vista = "FRONTAL"

            if cv2.getWindowProperty(VENTANA_TITULO, cv2.WND_PROP_VISIBLE) < 1:
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
