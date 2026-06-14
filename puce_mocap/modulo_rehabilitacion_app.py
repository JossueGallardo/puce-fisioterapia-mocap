"""Aplicacion final de Semana 5 / Modulo 2: rehabilitacion en vivo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

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
    _dibujar_icono_frames,
    _dibujar_icono_power,
    _dibujar_icono_refresh,
    _dibujar_icono_reps,
    _dibujar_icono_target,
    _dibujar_rectangulo_redondeado,
    _dibujar_tarjeta_base,
    _dibujar_texto,
    _dibujar_texto_centrado,
    _dibujar_x,
    _pegar_imagen_redondeada,
    _superponer_imagen,
    limitar_lineas_texto,
)
from puce_mocap.rehab_analyzer import (
    COLOR_AMARILLO,
    COLOR_ROJO,
    COLOR_VERDE as COLOR_VERDE_LOGICO,
    ESTADO_DENTRO_RANGO,
    ESTADO_POSTURA_INCOMPLETA,
    RehabAnalysisResult,
    evaluar_ejercicio_rehabilitacion,
)
from puce_mocap.rehab_profiles import cargar_perfil_paciente
from puce_mocap.rehab_report import generar_reporte_rehabilitacion_csv
from puce_mocap.rehab_session import RehabSession

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - se valida manualmente en Windows
    mp = None


VENTANA_TITULO = "PUCE MoCap - Módulo de Rehabilitación"
SUBTITULO = "Rangos terapéuticos configurables | Basado en FreeMoCap"
PERFIL_DEMO_PATH = REPO_ROOT / "profiles" / "paciente_demo.json"
REPORTE_REHAB_PATH = REPO_ROOT / "reports" / "semana_5_rehab_report.csv"
COLOR_AMARILLO_UI = (45, 205, 245)


@dataclass(frozen=True)
class EjercicioRehabConfig:
    tecla: str
    clave: str
    nombre: str
    nombre_corto: str


EJERCICIOS: dict[str, EjercicioRehabConfig] = {
    "1": EjercicioRehabConfig("1", "flexion_codo", "Flexión de codo", "Flexión codo"),
    "2": EjercicioRehabConfig("2", "abduccion_hombro", "Abducción de hombro", "Abducción hombro"),
    "3": EjercicioRehabConfig("3", "rotacion_muneca", "Rotación de muñeca", "Rotación muñeca"),
    "4": EjercicioRehabConfig("4", "extension_rodilla", "Extensión de rodilla", "Extensión rodilla"),
    "5": EjercicioRehabConfig("5", "dorsiflexion_tobillo", "Dorsiflexión de tobillo", "Dorsiflexión"),
    "6": EjercicioRehabConfig("6", "elevacion_pierna_recta", "Elevación de pierna recta", "Elevación pierna"),
}


def _punto_landmark(landmarks, landmark_id: int, min_visibility: float = 0.35) -> list[float] | None:
    landmark = landmarks[landmark_id]
    if getattr(landmark, "visibility", 1.0) < min_visibility:
        return None
    return [float(landmark.x), float(-landmark.y), float(-landmark.z)]


def mediapipe_a_esqueleto_rehab(pose_landmarks) -> dict[str, list[float]]:
    """Convierte landmarks de MediaPipe al formato del analizador rehab."""
    if mp is None:  # pragma: no cover
        return {}

    mp_pose = mp.solutions.pose
    landmarks = pose_landmarks.landmark
    mapa = {
        "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
        "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER.value,
        "right_elbow": mp_pose.PoseLandmark.RIGHT_ELBOW.value,
        "left_elbow": mp_pose.PoseLandmark.LEFT_ELBOW.value,
        "right_wrist": mp_pose.PoseLandmark.RIGHT_WRIST.value,
        "left_wrist": mp_pose.PoseLandmark.LEFT_WRIST.value,
        "right_index": mp_pose.PoseLandmark.RIGHT_INDEX.value,
        "left_index": mp_pose.PoseLandmark.LEFT_INDEX.value,
        "right_hip": mp_pose.PoseLandmark.RIGHT_HIP.value,
        "left_hip": mp_pose.PoseLandmark.LEFT_HIP.value,
        "right_knee": mp_pose.PoseLandmark.RIGHT_KNEE.value,
        "left_knee": mp_pose.PoseLandmark.LEFT_KNEE.value,
        "right_ankle": mp_pose.PoseLandmark.RIGHT_ANKLE.value,
        "left_ankle": mp_pose.PoseLandmark.LEFT_ANKLE.value,
        "right_foot": mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value,
        "left_foot": mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value,
    }
    esqueleto = {}
    for nombre, landmark_id in mapa.items():
        punto = _punto_landmark(landmarks, landmark_id)
        if punto is not None:
            esqueleto[nombre] = punto
    return esqueleto


def _color_estado(resultado: RehabAnalysisResult) -> tuple[int, int, int]:
    if resultado.color == COLOR_VERDE_LOGICO:
        return COLOR_VERDE
    if resultado.color == COLOR_AMARILLO:
        return COLOR_AMARILLO_UI
    return COLOR_ROJO_UI


def _etiqueta_estado(resultado: RehabAnalysisResult) -> str:
    if resultado.estado == ESTADO_DENTRO_RANGO:
        return "DENTRO DEL RANGO"
    if resultado.estado == ESTADO_POSTURA_INCOMPLETA:
        return "POSTURA INCOMPLETA"
    return "FUERA DEL RANGO"


def _resultado_inicial(ejercicio: EjercicioRehabConfig, perfil: Mapping[str, Any]) -> RehabAnalysisResult:
    return evaluar_ejercicio_rehabilitacion(ejercicio.clave, {}, perfil)


class ModuloRehabilitacionDashboard:
    """Renderer OpenCV coherente con los modulos de pesas y caminadora."""

    def __init__(self, perfil: Mapping[str, Any], ancho: int = ANCHO_DASHBOARD, alto: int = ALTO_DASHBOARD):
        self.perfil = perfil
        self.ancho = ancho
        self.alto = alto
        self.logo_puce = _cargar_logo(ASSETS_DIR / "logo_puce.png", 335, 92)
        self.logo_fe_alegria = _cargar_logo_fe_alegria(ASSETS_DIR / "logo_fe_alegria.png", 110, 104)
        self._bases: dict[str, np.ndarray] = {}

    def render(
        self,
        frame_camara: np.ndarray,
        ejercicio: EjercicioRehabConfig,
        resultado: RehabAnalysisResult,
        sesion: RehabSession,
    ) -> np.ndarray:
        lienzo = self._obtener_base(ejercicio).copy()
        self._dibujar_camara(lienzo, frame_camara)
        self._dibujar_estado(lienzo, ejercicio, resultado)
        self._dibujar_metricas(lienzo, sesion)
        return lienzo

    def _obtener_base(self, ejercicio: EjercicioRehabConfig) -> np.ndarray:
        if ejercicio.tecla not in self._bases:
            lienzo = _crear_fondo(self.ancho, self.alto)
            self._dibujar_header(lienzo)
            self._dibujar_base_camara(lienzo)
            self._dibujar_base_estado(lienzo, ejercicio)
            self._dibujar_panel_paciente(lienzo)
            self._dibujar_panel_ejercicios(lienzo, ejercicio)
            self._dibujar_base_metricas(lienzo)
            self._bases[ejercicio.tecla] = lienzo
        return self._bases[ejercicio.tecla]

    def _dibujar_header(self, lienzo: np.ndarray) -> None:
        if self.logo_puce is not None:
            _superponer_imagen(lienzo, self.logo_puce, 38, 52)
        else:
            _dibujar_texto(lienzo, "Pontificia Universidad Catolica del Ecuador", 38, 92, 0.50, COLOR_CYAN, 2)

        _dibujar_texto_centrado(lienzo, VENTANA_TITULO, self.ancho // 2, 91, 1.08, COLOR_TEXTO, 2)
        _dibujar_texto_centrado(lienzo, SUBTITULO, self.ancho // 2, 128, 0.58, COLOR_TEXTO_SUAVE, 1)

        if self.logo_fe_alegria is not None:
            _superponer_imagen(lienzo, self.logo_fe_alegria, self.ancho - 292, 48)
        _dibujar_texto(lienzo, "Fe y Alegria", self.ancho - 178, 91, 0.68, COLOR_TEXTO, 2)
        _dibujar_texto(lienzo, "Ecuador", self.ancho - 178, 124, 0.68, COLOR_TEXTO, 2)

    def _dibujar_base_camara(self, lienzo: np.ndarray) -> None:
        _dibujar_tarjeta_base(lienzo, 24, 156, 700, 524, 18)

    def _dibujar_camara(self, lienzo: np.ndarray, frame_camara: np.ndarray) -> None:
        x, y, w, h = 24, 156, 700, 524
        _pegar_imagen_redondeada(lienzo, frame_camara, x + 14, y + 14, w - 28, h - 28, 14)
        _dibujar_rectangulo_redondeado(lienzo, x + 14, y + 14, w - 28, h - 28, 14, (55, 57, 45), 1)
        _dibujar_rectangulo_redondeado(lienzo, x + 24, y + 26, 105, 34, 15, (36, 37, 38), -1)
        cv2.circle(lienzo, (x + 45, y + 43), 6, COLOR_VERDE, -1, cv2.LINE_AA)
        _dibujar_texto(lienzo, "EN VIVO", x + 61, y + 51, 0.42, COLOR_TEXTO, 2)

    def _dibujar_base_estado(self, lienzo: np.ndarray, ejercicio: EjercicioRehabConfig) -> None:
        x, y, w, h = 745, 156, 480, 390
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        _dibujar_icono_target(lienzo, x + 28, y + 17, COLOR_CYAN)
        _dibujar_texto(lienzo, "EJERCICIO ACTUAL", x + 76, y + 39, 0.41, COLOR_TEXTO_SUAVE, 2)
        _dibujar_texto(lienzo, ejercicio.nombre, x + 32, y + 87, 0.65, COLOR_TEXTO, 2)
        configuracion = self.perfil["ejercicios"][ejercicio.clave]
        rango = f"Rango objetivo: {configuracion['angulo_minimo']:.0f} - {configuracion['angulo_maximo']:.0f} grados"
        _dibujar_texto(lienzo, rango, x + 32, y + 126, 0.48, COLOR_TEXTO_SUAVE, 1)

    def _dibujar_estado(
        self, lienzo: np.ndarray, ejercicio: EjercicioRehabConfig, resultado: RehabAnalysisResult
    ) -> None:
        x, y = 745, 156
        color = _color_estado(resultado)
        valor = "N/D" if resultado.angulo_actual is None else f"{resultado.angulo_actual:.0f}"
        _dibujar_texto(lienzo, valor, x + 32, y + 205, 1.72, color, 2)
        if resultado.angulo_actual is not None:
            _dibujar_texto(lienzo, "grados", x + 155, y + 202, 0.46, COLOR_TEXTO_SUAVE, 1)

        _dibujar_rectangulo_redondeado(lienzo, x + 30, y + 224, 420, 58, 10, (46, 43, 30), -1)
        _dibujar_rectangulo_redondeado(lienzo, x + 30, y + 224, 420, 58, 10, color, 2)
        if resultado.dentro_rango:
            _dibujar_check(lienzo, (x + 66, y + 253), 16, color)
        else:
            _dibujar_x(lienzo, (x + 66, y + 253), 16, color)
        _dibujar_texto_centrado(lienzo, _etiqueta_estado(resultado), x + 260, y + 263, 0.51, COLOR_TEXTO, 2)

        mensaje = resultado.mensajes[0] if resultado.mensajes else "Sesion iniciada."
        lineas = limitar_lineas_texto(mensaje, 390, 0.46, 1, 3)
        for indice, linea in enumerate(lineas):
            _dibujar_texto(lienzo, linea, x + 42, y + 323 + indice * 27, 0.46, COLOR_TEXTO, 1)

    def _dibujar_panel_paciente(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 745, 565, 480, 115
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 15)
        _dibujar_icono_chart(lienzo, x + 24, y + 17, COLOR_TEXTO_MUTED)
        _dibujar_texto(lienzo, "PERFIL FICTICIO", x + 70, y + 38, 0.42, COLOR_TEXTO_SUAVE, 2)
        _dibujar_texto(
            lienzo,
            f"{self.perfil['codigo_paciente']} | {self.perfil['nombre']}",
            x + 24,
            y + 70,
            0.50,
            COLOR_TEXTO,
            2,
        )
        lesion = limitar_lineas_texto(str(self.perfil["lesion"]), w - 48, 0.40, 1, 1)[0]
        _dibujar_texto(lienzo, lesion, x + 24, y + 98, 0.40, COLOR_TEXTO_SUAVE, 1)

    def _dibujar_panel_ejercicios(self, lienzo: np.ndarray, ejercicio: EjercicioRehabConfig) -> None:
        x, y, w, h = 1245, 156, 330, 524
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        _dibujar_icono_chart(lienzo, x + 24, y + 16, COLOR_TEXTO_MUTED)
        _dibujar_texto(lienzo, "EJERCICIOS", x + 70, y + 37, 0.43, COLOR_TEXTO_SUAVE, 2)

        for indice, config in enumerate(EJERCICIOS.values()):
            boton_y = y + 54 + indice * 42
            seleccionado = config.tecla == ejercicio.tecla
            relleno = (70, 82, 47) if seleccionado else COLOR_TARJETA_SUAVE
            borde = COLOR_CYAN if seleccionado else COLOR_BORDE
            _dibujar_rectangulo_redondeado(lienzo, x + 18, boton_y, w - 36, 36, 7, relleno, -1)
            _dibujar_rectangulo_redondeado(lienzo, x + 18, boton_y, w - 36, 36, 7, borde, 2 if seleccionado else 1)
            _dibujar_texto(lienzo, config.tecla, x + 34, boton_y + 25, 0.43, COLOR_CYAN, 2)
            _dibujar_texto(lienzo, config.nombre_corto, x + 62, boton_y + 25, 0.40, COLOR_TEXTO, 1)

        controles = (
            ("r", "Reiniciar", COLOR_AZUL, _dibujar_icono_refresh),
            ("g", "Guardar reporte", COLOR_VERDE, _dibujar_icono_target),
            ("q", "Salir", COLOR_ROJO_UI, _dibujar_icono_power),
        )
        for indice, (tecla, texto, color, icono) in enumerate(controles):
            boton_y = y + 322 + indice * 58
            _dibujar_rectangulo_redondeado(lienzo, x + 18, boton_y, w - 36, 48, 8, (42, 36, 34), -1)
            _dibujar_rectangulo_redondeado(lienzo, x + 18, boton_y, w - 36, 48, 8, color, 1)
            icono(lienzo, x + 30, boton_y + 4, color)
            _dibujar_texto(lienzo, tecla.upper(), x + 80, boton_y + 31, 0.45, color, 2)
            _dibujar_texto(lienzo, texto, x + 112, boton_y + 31, 0.43, COLOR_TEXTO, 1)

    def _dibujar_base_metricas(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 24, 704, 1552, 152
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 16)
        titulos = ("REPETICIONES", "DENTRO DEL RANGO", "ANGULO MAXIMO", "FRAMES VALIDOS")
        iconos = (_dibujar_icono_reps, _dibujar_icono_target, _dibujar_icono_chart, _dibujar_icono_frames)
        ancho_columna = w // 4
        for indice, (titulo, icono) in enumerate(zip(titulos, iconos)):
            col_x = x + indice * ancho_columna
            if indice:
                cv2.line(lienzo, (col_x, y + 18), (col_x, y + h - 18), COLOR_BORDE, 1)
            icono(lienzo, col_x + 34, y + 20, COLOR_TEXTO_MUTED)
            _dibujar_texto(lienzo, titulo, col_x + 82, y + 43, 0.39, COLOR_TEXTO_SUAVE, 2)

    def _dibujar_metricas(self, lienzo: np.ndarray, sesion: RehabSession) -> None:
        x, y, w = 24, 704, 1552
        ancho_columna = w // 4
        maximo = "N/D" if sesion.angulo_maximo_alcanzado is None else f"{sesion.angulo_maximo_alcanzado:.0f} grados"
        valores = (
            str(sesion.repeticiones_estimadas),
            f"{sesion.porcentaje_dentro_rango:.0f}%",
            maximo,
            str(sesion.frames_validos),
        )
        colores = (COLOR_TEXTO, COLOR_VERDE, COLOR_AZUL, COLOR_TEXTO)
        for indice, (valor, color) in enumerate(zip(valores, colores)):
            col_x = x + indice * ancho_columna
            _dibujar_texto_centrado(lienzo, valor, col_x + ancho_columna // 2, y + 104, 0.76, color, 2)
        _dibujar_barra(
            lienzo,
            x + ancho_columna + 70,
            y + 122,
            ancho_columna - 140,
            9,
            sesion.porcentaje_dentro_rango / 100.0,
            COLOR_VERDE,
        )


def _nueva_sesion(ejercicio: EjercicioRehabConfig, perfil: Mapping[str, Any]) -> RehabSession:
    return RehabSession(ejercicio.clave, str(perfil["codigo_paciente"]))


def _guardar_reporte(sesion: RehabSession, perfil: Mapping[str, Any]) -> Path:
    ruta = generar_reporte_rehabilitacion_csv(sesion.exportar_resumen(), perfil, REPORTE_REHAB_PATH)
    print(f"Reporte CSV generado: {ruta}")
    return ruta


def main(ruta_perfil: str | Path | None = None) -> None:
    """Ejecuta la interfaz de rehabilitacion con el perfil ficticio indicado."""
    if mp is None:
        print("MediaPipe no esta instalado. Ejecuta: python -m pip install mediapipe")
        return

    ruta = Path(ruta_perfil) if ruta_perfil is not None else PERFIL_DEMO_PATH
    try:
        perfil = cargar_perfil_paciente(ruta)
    except (OSError, ValueError) as exc:
        print(f"No se pudo cargar el perfil de rehabilitacion: {exc}")
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

    ejercicio = EJERCICIOS["1"]
    sesion = _nueva_sesion(ejercicio, perfil)
    resultado = _resultado_inicial(ejercicio, perfil)
    dashboard = ModuloRehabilitacionDashboard(perfil)

    cv2.namedWindow(VENTANA_TITULO, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(VENTANA_TITULO, dashboard.ancho, dashboard.alto)
    print("PUCE MoCap - Módulo de Rehabilitación iniciado con perfil ficticio.")
    print("Teclas: 1-6 ejercicios | r reiniciar | g guardar reporte | q salir")

    with mp_pose.Pose(model_complexity=1, min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer un frame de la camara.")
                break

            frame = cv2.flip(frame, 1)
            resultado_pose = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frame_visual = frame.copy()
            if resultado_pose.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame_visual,
                    resultado_pose.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=landmark_spec,
                    connection_drawing_spec=connection_spec,
                )
                esqueleto = mediapipe_a_esqueleto_rehab(resultado_pose.pose_landmarks)
                resultado = evaluar_ejercicio_rehabilitacion(ejercicio.clave, esqueleto, perfil)
            else:
                resultado = _resultado_inicial(ejercicio, perfil)

            sesion.registrar_resultado(resultado)
            cv2.imshow(VENTANA_TITULO, dashboard.render(frame_visual, ejercicio, resultado, sesion))

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                if sesion.frames_validos > 0:
                    _guardar_reporte(sesion, perfil)
                break
            if tecla in tuple(ord(numero) for numero in EJERCICIOS):
                ejercicio = EJERCICIOS[chr(tecla)]
                sesion = _nueva_sesion(ejercicio, perfil)
                resultado = _resultado_inicial(ejercicio, perfil)
            elif tecla == ord("r"):
                sesion.reiniciar()
            elif tecla == ord("g"):
                _guardar_reporte(sesion, perfil)

            if cv2.getWindowProperty(VENTANA_TITULO, cv2.WND_PROP_VISIBLE) < 1:
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
