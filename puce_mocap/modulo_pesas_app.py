"""Aplicacion final de Semana 3 / Modulo 1: ejercicios con pesas en vivo.

Este modulo mantiene la logica PUCE separada del nucleo de FreeMoCap y usa
MediaPipe Pose solo como complemento para el prototipo con camara en vivo.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import time
from typing import Callable, Mapping, Sequence

import cv2
import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - OpenCV queda como respaldo visual
    Image = None
    ImageDraw = None
    ImageFont = None

from puce_mocap.exercise_report import generar_reporte_csv
from puce_mocap.exercise_rules import (
    COLOR_ROJO,
    ESTADO_CORREGIR,
    ExerciseFeedback,
    evaluar_peso_muerto,
    evaluar_press_hombro,
    evaluar_sentadilla,
)
from puce_mocap.exercise_session import ExerciseSession

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - se valida manualmente en Windows
    mp = None


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"
REPORTE_LIVE_PATH = REPO_ROOT / "reports" / "semana_3_live_pose_report.csv"

VENTANA_TITULO = "PUCE MoCap - Modulo de Pesas"
SUBTITULO = "Basado en FreeMoCap | MediaPipe Pose como complemento en vivo"
MENSAJE_POSTURA_INCOMPLETA = "Alejate de la camara hasta que se vean cabeza, cadera, rodillas, tobillos y pies."

ANCHO_DASHBOARD = 1600
ALTO_DASHBOARD = 900

COLOR_FONDO_SUPERIOR = np.array([20, 14, 7], dtype=np.float32)
COLOR_FONDO_INFERIOR = np.array([34, 26, 10], dtype=np.float32)
COLOR_TARJETA = (34, 28, 18)
COLOR_TARJETA_SUAVE = (43, 36, 24)
COLOR_BORDE = (58, 53, 39)
COLOR_BORDE_SUAVE = (42, 40, 31)
COLOR_TEXTO = (246, 248, 250)
COLOR_TEXTO_SUAVE = (181, 193, 205)
COLOR_TEXTO_MUTED = (133, 150, 163)
COLOR_CYAN = (225, 192, 28)
COLOR_CYAN_OSCURO = (98, 74, 15)
COLOR_VERDE = (100, 224, 94)
COLOR_VERDE_OSCURO = (42, 102, 43)
COLOR_ROJO_UI = (70, 78, 238)
COLOR_ROJO_OSCURO = (48, 35, 82)
COLOR_AZUL = (244, 139, 72)
COLOR_BARRA_FONDO = (49, 59, 62)


Evaluador = Callable[..., ExerciseFeedback]


@dataclass(frozen=True)
class EjercicioConfig:
    """Configuracion visual y funcional de un ejercicio del Modulo 1."""

    tecla: str
    nombre: str
    evaluador: Evaluador
    angulo_principal: str


EJERCICIOS: dict[str, EjercicioConfig] = {
    "1": EjercicioConfig("1", "Sentadilla", evaluar_sentadilla, "angulo_rodilla"),
    "2": EjercicioConfig("2", "Press de hombro", evaluar_press_hombro, "angulo_codo"),
    "3": EjercicioConfig("3", "Peso muerto", evaluar_peso_muerto, "desviacion_tronco"),
}

LANDMARKS_POSTURA_BASE = (
    "nose",
    "right_hip",
    "left_hip",
    "right_knee",
    "left_knee",
    "right_ankle",
    "left_ankle",
    "right_foot",
    "left_foot",
)

LANDMARKS_REQUERIDOS = {
    "Sentadilla": LANDMARKS_POSTURA_BASE + ("right_shoulder",),
    "Press de hombro": LANDMARKS_POSTURA_BASE + ("right_shoulder", "right_elbow", "right_wrist"),
    "Peso muerto": LANDMARKS_POSTURA_BASE + ("right_shoulder",),
}


def formatear_duracion(segundos: float) -> str:
    """Convierte segundos a formato HH:MM:SS para la tarjeta de sesion."""
    segundos_enteros = max(0, int(segundos))
    horas, resto = divmod(segundos_enteros, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def describir_calidad_global(porcentaje_correcto: float, total_frames: int) -> str:
    """Entrega una etiqueta simple, no clinica, para resumir la sesion."""
    if total_frames == 0:
        return "N/D"
    if porcentaje_correcto >= 75.0:
        return "Buena"
    if porcentaje_correcto >= 50.0:
        return "En progreso"
    return "Revisar tecnica"


def dividir_texto(texto: str, ancho_maximo: int, escala: float, grosor: int) -> list[str]:
    """Divide texto para que entre en el ancho disponible del panel."""
    palabras = texto.split()
    if not palabras:
        return []

    lineas: list[str] = []
    linea_actual = palabras[0]
    for palabra in palabras[1:]:
        candidata = f"{linea_actual} {palabra}"
        ancho = _medir_texto(candidata, escala, grosor)[0]
        if ancho <= ancho_maximo:
            linea_actual = candidata
        else:
            lineas.append(linea_actual)
            linea_actual = palabra
    lineas.append(linea_actual)
    return lineas


def limitar_lineas_texto(texto: str, ancho_maximo: int, escala: float, grosor: int, max_lineas: int) -> list[str]:
    """Divide texto y compacta el remanente para que no salga del panel."""
    lineas = dividir_texto(texto, ancho_maximo, escala, grosor)
    if len(lineas) <= max_lineas:
        return lineas

    lineas_visibles = lineas[: max_lineas - 1]
    ultima_linea = " ".join(lineas[max_lineas - 1 :])
    while _medir_texto(ultima_linea + "...", escala, grosor)[0] > ancho_maximo and " " in ultima_linea:
        ultima_linea = ultima_linea.rsplit(" ", 1)[0]
    lineas_visibles.append(ultima_linea.rstrip() + "...")
    return lineas_visibles


def postura_completa(esqueleto: Mapping[str, Sequence[float]], ejercicio: str) -> bool:
    """Valida que existan los landmarks minimos antes de evaluar y registrar frames."""
    requeridos = LANDMARKS_REQUERIDOS[ejercicio]
    return all(nombre in esqueleto for nombre in requeridos)


def _feedback_incompleto(ejercicio: str) -> ExerciseFeedback:
    return ExerciseFeedback(
        ejercicio=ejercicio,
        estado=ESTADO_CORREGIR,
        color=COLOR_ROJO,
        angulos={},
        mensajes=[MENSAJE_POSTURA_INCOMPLETA],
    )


def _punto_landmark(landmarks, landmark_id: int, min_visibility: float = 0.35) -> list[float] | None:
    landmark = landmarks[landmark_id]
    if getattr(landmark, "visibility", 1.0) < min_visibility:
        return None
    return [float(landmark.x), float(-landmark.y), float(-landmark.z)]


def mediapipe_a_esqueleto_3d(pose_landmarks) -> dict[str, list[float]]:
    """Convierte landmarks de MediaPipe Pose al formato usado por exercise_rules."""
    if mp is None:  # pragma: no cover - main no llama esta funcion sin MediaPipe
        return {}

    mp_pose = mp.solutions.pose
    landmarks = pose_landmarks.landmark
    mapa = {
        "nose": mp_pose.PoseLandmark.NOSE.value,
        "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
        "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER.value,
        "right_elbow": mp_pose.PoseLandmark.RIGHT_ELBOW.value,
        "left_elbow": mp_pose.PoseLandmark.LEFT_ELBOW.value,
        "right_wrist": mp_pose.PoseLandmark.RIGHT_WRIST.value,
        "left_wrist": mp_pose.PoseLandmark.LEFT_WRIST.value,
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


def evaluar_esqueleto(ejercicio: EjercicioConfig, esqueleto: Mapping[str, Sequence[float]]) -> ExerciseFeedback:
    """Evalua un esqueleto valido con las reglas ya implementadas del Modulo 1."""
    if not postura_completa(esqueleto, ejercicio.nombre):
        return _feedback_incompleto(ejercicio.nombre)

    try:
        if ejercicio.nombre == "Press de hombro":
            return ejercicio.evaluador(esqueleto, lado="right")
        return ejercicio.evaluador(esqueleto)
    except ValueError:
        return _feedback_incompleto(ejercicio.nombre)


def _crear_fondo(ancho: int, alto: int) -> np.ndarray:
    mezcla = np.linspace(0.0, 1.0, alto, dtype=np.float32)[:, None]
    filas = COLOR_FONDO_SUPERIOR * (1.0 - mezcla) + COLOR_FONDO_INFERIOR * mezcla
    fondo = np.repeat(filas[:, None, :], ancho, axis=1)

    x = np.linspace(-1.0, 1.0, ancho, dtype=np.float32)[None, :]
    y = np.linspace(-1.0, 1.0, alto, dtype=np.float32)[:, None]
    luz_central = np.clip(1.0 - np.sqrt((x * 0.82) ** 2 + (y * 1.15) ** 2), 0.0, 1.0)
    fondo += luz_central[:, :, None] * np.array([18, 12, 5], dtype=np.float32)

    luz_cyan = np.exp(-((x + 0.72) ** 2 + (y - 0.72) ** 2) / 0.35)
    fondo += luz_cyan[:, :, None] * np.array([18, 12, 0], dtype=np.float32)
    return np.clip(fondo, 0, 255).astype(np.uint8)


def _color_bgr_a_rgb(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return int(color[2]), int(color[1]), int(color[0])


@lru_cache(maxsize=48)
def _fuente(size: int, bold: bool = False):
    if ImageFont is None:
        return None

    candidatos = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for ruta in candidatos:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, size=size)
    return ImageFont.load_default()


def _tamano_fuente(escala: float) -> int:
    return max(10, int(round(escala * 39.0)))


def _medir_texto(texto: str, escala: float, grosor: int = 1) -> tuple[int, int]:
    if Image is None or ImageDraw is None or ImageFont is None:
        return cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, escala, grosor)[0]

    fuente = _fuente(_tamano_fuente(escala), grosor >= 2)
    capa = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _dibujar_rectangulo_redondeado(
    imagen: np.ndarray,
    x: int,
    y: int,
    ancho: int,
    alto: int,
    radio: int,
    color: tuple[int, int, int] | int,
    grosor: int = -1,
) -> None:
    radio = max(0, min(radio, ancho // 2, alto // 2))
    if grosor < 0:
        cv2.rectangle(imagen, (x + radio, y), (x + ancho - radio, y + alto), color, -1)
        cv2.rectangle(imagen, (x, y + radio), (x + ancho, y + alto - radio), color, -1)
        cv2.circle(imagen, (x + radio, y + radio), radio, color, -1)
        cv2.circle(imagen, (x + ancho - radio, y + radio), radio, color, -1)
        cv2.circle(imagen, (x + radio, y + alto - radio), radio, color, -1)
        cv2.circle(imagen, (x + ancho - radio, y + alto - radio), radio, color, -1)
        return

    cv2.line(imagen, (x + radio, y), (x + ancho - radio, y), color, grosor, cv2.LINE_AA)
    cv2.line(imagen, (x + radio, y + alto), (x + ancho - radio, y + alto), color, grosor, cv2.LINE_AA)
    cv2.line(imagen, (x, y + radio), (x, y + alto - radio), color, grosor, cv2.LINE_AA)
    cv2.line(imagen, (x + ancho, y + radio), (x + ancho, y + alto - radio), color, grosor, cv2.LINE_AA)
    cv2.ellipse(imagen, (x + radio, y + radio), (radio, radio), 180, 0, 90, color, grosor, cv2.LINE_AA)
    cv2.ellipse(imagen, (x + ancho - radio, y + radio), (radio, radio), 270, 0, 90, color, grosor, cv2.LINE_AA)
    cv2.ellipse(
        imagen, (x + ancho - radio, y + alto - radio), (radio, radio), 0, 0, 90, color, grosor, cv2.LINE_AA
    )
    cv2.ellipse(imagen, (x + radio, y + alto - radio), (radio, radio), 90, 0, 90, color, grosor, cv2.LINE_AA)


def _mezclar_overlay(base: np.ndarray, overlay: np.ndarray, alpha: float) -> None:
    cv2.addWeighted(overlay, alpha, base, 1.0 - alpha, 0, dst=base)


def _dibujar_sombra(
    imagen: np.ndarray,
    x: int,
    y: int,
    ancho: int,
    alto: int,
    radio: int,
    color: tuple[int, int, int],
    alpha: float = 0.28,
    blur: int = 25,
) -> None:
    pad = max(6, blur)
    local_w = ancho + pad * 2
    local_h = alto + pad * 2
    mascara = np.zeros((local_h, local_w), dtype=np.uint8)
    _dibujar_rectangulo_redondeado(mascara, pad, pad, ancho, alto, radio, 255, -1)
    mascara = cv2.GaussianBlur(mascara, (blur | 1, blur | 1), 0)

    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(imagen.shape[1], x + ancho + pad)
    y1 = min(imagen.shape[0], y + alto + pad)
    if x0 >= x1 or y0 >= y1:
        return

    mx0 = x0 - (x - pad)
    my0 = y0 - (y - pad)
    mx1 = mx0 + (x1 - x0)
    my1 = my0 + (y1 - y0)
    mascara_roi = mascara[my0:my1, mx0:mx1]
    alpha_mascara = (mascara_roi.astype(np.float32) / 255.0 * alpha)[:, :, None]
    roi = imagen[y0:y1, x0:x1]
    capa_color = np.full_like(roi, color)
    roi[:] = (capa_color * alpha_mascara + roi * (1.0 - alpha_mascara)).astype(np.uint8)


def _dibujar_tarjeta_base(
    imagen: np.ndarray,
    x: int,
    y: int,
    ancho: int,
    alto: int,
    radio: int = 18,
    relleno: tuple[int, int, int] = COLOR_TARJETA,
    borde: tuple[int, int, int] = COLOR_BORDE,
) -> None:
    _dibujar_sombra(imagen, x + 3, y + 8, ancho, alto, radio, (0, 0, 0), 0.32, 31)
    _dibujar_sombra(imagen, x - 1, y - 1, ancho + 2, alto + 2, radio + 2, COLOR_CYAN, 0.06, 35)
    _dibujar_rectangulo_redondeado(imagen, x, y, ancho, alto, radio, relleno, -1)
    brillo = imagen.copy()
    _dibujar_rectangulo_redondeado(brillo, x + 1, y + 1, ancho - 2, max(2, alto // 2), radio, (50, 44, 31), -1)
    _mezclar_overlay(imagen, brillo, 0.18)
    _dibujar_rectangulo_redondeado(imagen, x, y, ancho, alto, radio, COLOR_BORDE_SUAVE, 2)
    _dibujar_rectangulo_redondeado(imagen, x + 1, y + 1, ancho - 2, alto - 2, max(4, radio - 2), borde, 1)


def _dibujar_texto(
    imagen: np.ndarray,
    texto: str,
    x: int,
    y: int,
    escala: float,
    color: tuple[int, int, int] = COLOR_TEXTO,
    grosor: int = 1,
) -> None:
    if Image is None or ImageDraw is None or ImageFont is None:
        cv2.putText(imagen, texto, (x, y), cv2.FONT_HERSHEY_SIMPLEX, escala, color, grosor, cv2.LINE_AA)
        return

    size = _tamano_fuente(escala)
    fuente = _fuente(size, grosor >= 2)
    ancho, alto = _medir_texto(texto, escala, grosor)
    if ancho <= 0 or alto <= 0:
        return

    margen = max(4, size // 5)
    capa = Image.new("RGBA", (ancho + margen * 2, alto + margen * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    draw.text((margen - bbox[0], margen - bbox[1]), texto, font=fuente, fill=(*_color_bgr_a_rgb(color), 255))
    texto_bgra = cv2.cvtColor(np.array(capa), cv2.COLOR_RGBA2BGRA)
    _superponer_imagen(imagen, texto_bgra, x - margen, y - alto - margen + 2)


def _dibujar_texto_centrado(
    imagen: np.ndarray,
    texto: str,
    centro_x: int,
    y: int,
    escala: float,
    color: tuple[int, int, int] = COLOR_TEXTO,
    grosor: int = 1,
) -> None:
    ancho = _medir_texto(texto, escala, grosor)[0]
    _dibujar_texto(imagen, texto, centro_x - ancho // 2, y, escala, color, grosor)


def _redimensionar_contenido(imagen: np.ndarray, ancho_destino: int, alto_destino: int) -> np.ndarray:
    alto, ancho = imagen.shape[:2]
    escala = min(ancho_destino / ancho, alto_destino / alto)
    nuevo_ancho = max(1, int(ancho * escala))
    nuevo_alto = max(1, int(alto * escala))
    return cv2.resize(imagen, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)


def _redimensionar_cover(imagen: np.ndarray, ancho_destino: int, alto_destino: int) -> np.ndarray:
    alto, ancho = imagen.shape[:2]
    escala = max(ancho_destino / ancho, alto_destino / alto)
    nuevo_ancho = max(1, int(ancho * escala))
    nuevo_alto = max(1, int(alto * escala))
    redimensionada = cv2.resize(imagen, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_AREA)
    inicio_x = max(0, (nuevo_ancho - ancho_destino) // 2)
    inicio_y = max(0, (nuevo_alto - alto_destino) // 2)
    return redimensionada[inicio_y : inicio_y + alto_destino, inicio_x : inicio_x + ancho_destino]


def _recortar_alpha(imagen: np.ndarray, margen: int = 0) -> np.ndarray:
    if imagen.ndim != 3 or imagen.shape[2] != 4:
        return imagen
    alpha = imagen[:, :, 3]
    bbox = cv2.boundingRect((alpha > 0).astype(np.uint8))
    x, y, w, h = bbox
    if w == 0 or h == 0:
        return imagen
    x0 = max(0, x - margen)
    y0 = max(0, y - margen)
    x1 = min(imagen.shape[1], x + w + margen)
    y1 = min(imagen.shape[0], y + h + margen)
    return imagen[y0:y1, x0:x1]


def _superponer_imagen(base: np.ndarray, imagen: np.ndarray, x: int, y: int) -> None:
    alto, ancho = imagen.shape[:2]
    if x >= base.shape[1] or y >= base.shape[0]:
        return

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(base.shape[1], x + ancho)
    y2 = min(base.shape[0], y + alto)
    if x1 >= x2 or y1 >= y2:
        return

    recorte = imagen[y1 - y : y2 - y, x1 - x : x2 - x]
    roi = base[y1:y2, x1:x2]
    if recorte.ndim == 3 and recorte.shape[2] == 4:
        alpha = recorte[:, :, 3:4].astype(np.float32) / 255.0
        roi[:] = (alpha * recorte[:, :, :3] + (1.0 - alpha) * roi).astype(np.uint8)
    else:
        roi[:] = recorte[:, :, :3]


def _pegar_imagen_redondeada(base: np.ndarray, imagen: np.ndarray, x: int, y: int, ancho: int, alto: int, radio: int) -> None:
    recorte = _redimensionar_cover(imagen, ancho, alto)
    mascara = np.zeros((alto, ancho), dtype=np.uint8)
    _dibujar_rectangulo_redondeado(mascara, 0, 0, ancho - 1, alto - 1, radio, 255, -1)
    roi = base[y : y + alto, x : x + ancho]
    roi[mascara > 0] = recorte[mascara > 0]


def _cargar_logo(ruta: Path, ancho_maximo: int, alto_maximo: int) -> np.ndarray | None:
    if not ruta.exists():
        return None
    logo = cv2.imread(str(ruta), cv2.IMREAD_UNCHANGED)
    if logo is None:
        return None
    logo = _recortar_alpha(logo, margen=6)
    return _redimensionar_contenido(logo, ancho_maximo, alto_maximo)


def _cargar_logo_fe_alegria(ruta: Path, ancho_maximo: int, alto_maximo: int) -> np.ndarray | None:
    if not ruta.exists():
        return None
    logo = cv2.imread(str(ruta), cv2.IMREAD_UNCHANGED)
    if logo is None:
        return None
    logo_limpio = _limpiar_logo_fe_alegria(logo)
    return _redimensionar_contenido(logo_limpio, ancho_maximo, alto_maximo)


def _limpiar_logo_fe_alegria(logo: np.ndarray) -> np.ndarray:
    """Elimina fondos claros conectados al borde y conserva el simbolo institucional."""
    if logo.ndim != 3:
        return logo

    if logo.shape[2] == 3:
        rgba = cv2.cvtColor(logo, cv2.COLOR_BGR2BGRA)
    else:
        rgba = logo.copy()

    bgr = rgba[:, :, :3]
    b, g, r = cv2.split(bgr)
    rojo_logo = (r > 150) & (g < 120) & (b < 120)
    fondo_candidato = (~rojo_logo) & (r > 170) & (g > 170) & (b > 170)

    alto, ancho = fondo_candidato.shape
    mascara_ff = np.zeros((alto + 2, ancho + 2), dtype=np.uint8)
    relleno = fondo_candidato.astype(np.uint8) * 255
    for px, py in [(0, 0), (ancho - 1, 0), (0, alto - 1), (ancho - 1, alto - 1)]:
        if relleno[py, px] == 255:
            cv2.floodFill(relleno, mascara_ff, (px, py), 128)

    fondo_conectado = relleno == 128
    rgba[fondo_conectado, 3] = 0

    alpha = rgba[:, :, 3]
    bbox = cv2.boundingRect((alpha > 0).astype(np.uint8))
    x, y, w, h = bbox
    if w > 0 and h > 0:
        margen = 8
        x0 = max(0, x - margen)
        y0 = max(0, y - margen)
        x1 = min(rgba.shape[1], x + w + margen)
        y1 = min(rgba.shape[0], y + h + margen)
        rgba = rgba[y0:y1, x0:x1]
    return rgba


def _dibujar_barra(
    imagen: np.ndarray,
    x: int,
    y: int,
    ancho: int,
    alto: int,
    progreso: float,
    color: tuple[int, int, int],
) -> None:
    _dibujar_rectangulo_redondeado(imagen, x, y, ancho, alto, alto // 2, COLOR_BARRA_FONDO, -1)
    ancho_activo = int(ancho * min(1.0, max(0.0, progreso)))
    if ancho_activo > 0:
        _dibujar_rectangulo_redondeado(imagen, x, y, ancho_activo, alto, alto // 2, color, -1)


def _dibujar_check(imagen: np.ndarray, centro: tuple[int, int], radio: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, centro, radio, color, -1, cv2.LINE_AA)
    x, y = centro
    cv2.line(imagen, (x - radio // 2, y), (x - radio // 8, y + radio // 3), (245, 255, 245), 3, cv2.LINE_AA)
    cv2.line(imagen, (x - radio // 8, y + radio // 3), (x + radio // 2, y - radio // 3), (245, 255, 245), 3, cv2.LINE_AA)


def _dibujar_x(imagen: np.ndarray, centro: tuple[int, int], radio: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, centro, radio, color, -1, cv2.LINE_AA)
    x, y = centro
    cv2.line(imagen, (x - radio // 3, y - radio // 3), (x + radio // 3, y + radio // 3), (245, 245, 255), 3, cv2.LINE_AA)
    cv2.line(imagen, (x + radio // 3, y - radio // 3), (x - radio // 3, y + radio // 3), (245, 245, 255), 3, cv2.LINE_AA)


def _dibujar_icono_modulo(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, (x + 15, y + 12), 5, color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 15, y + 17), (x + 15, y + 31), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 15, y + 22), (x + 6, y + 28), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 15, y + 22), (x + 26, y + 16), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 15, y + 31), (x + 8, y + 41), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 15, y + 31), (x + 27, y + 38), color, 2, cv2.LINE_AA)


def _dibujar_icono_sentadilla(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, (x + 18, y + 9), 4, color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 17, y + 14), (x + 11, y + 27), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 11, y + 27), (x + 24, y + 31), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 24, y + 31), (x + 30, y + 43), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 11, y + 27), (x + 4, y + 40), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 18, y + 17), (x + 32, y + 17), color, 2, cv2.LINE_AA)


def _dibujar_icono_barra(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.line(imagen, (x + 2, y + 22), (x + 38, y + 22), color, 2, cv2.LINE_AA)
    for dx in (4, 9, 29, 34):
        cv2.line(imagen, (x + dx, y + 11), (x + dx, y + 33), color, 2, cv2.LINE_AA)
    cv2.circle(imagen, (x + 20, y + 22), 3, color, -1, cv2.LINE_AA)


def _dibujar_icono_refresh(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.ellipse(imagen, (x + 20, y + 21), (14, 14), 0, 35, 310, color, 2, cv2.LINE_AA)
    pts = np.array([[x + 31, y + 10], [x + 34, y + 21], [x + 24, y + 18]], dtype=np.int32)
    cv2.fillConvexPoly(imagen, pts, color, cv2.LINE_AA)


def _dibujar_icono_power(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, (x + 20, y + 24), 13, color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 20, y + 8), (x + 20, y + 22), color, 3, cv2.LINE_AA)


def _dibujar_icono_reps(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    _dibujar_icono_refresh(imagen, x, y, color)
    cv2.circle(imagen, (x + 20, y + 21), 3, color, -1, cv2.LINE_AA)


def _dibujar_icono_target(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, (x + 20, y + 21), 13, color, 2, cv2.LINE_AA)
    cv2.circle(imagen, (x + 20, y + 21), 5, color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 20, y + 4), (x + 20, y + 10), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 20, y + 32), (x + 20, y + 38), color, 2, cv2.LINE_AA)


def _dibujar_icono_frames(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    _dibujar_rectangulo_redondeado(imagen, x + 8, y + 10, 24, 24, 4, color, 2)
    cv2.line(imagen, (x + 13, y + 16), (x + 27, y + 28), color, 1, cv2.LINE_AA)
    cv2.line(imagen, (x + 27, y + 16), (x + 13, y + 28), color, 1, cv2.LINE_AA)


def _dibujar_icono_reloj(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.circle(imagen, (x + 20, y + 21), 14, color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 20, y + 21), (x + 20, y + 11), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 20, y + 21), (x + 29, y + 26), color, 2, cv2.LINE_AA)


def _dibujar_icono_chart(imagen: np.ndarray, x: int, y: int, color: tuple[int, int, int]) -> None:
    cv2.line(imagen, (x + 8, y + 33), (x + 8, y + 10), color, 2, cv2.LINE_AA)
    cv2.line(imagen, (x + 8, y + 33), (x + 34, y + 33), color, 2, cv2.LINE_AA)
    cv2.rectangle(imagen, (x + 13, y + 23), (x + 17, y + 32), color, -1)
    cv2.rectangle(imagen, (x + 21, y + 16), (x + 25, y + 32), color, -1)
    cv2.rectangle(imagen, (x + 29, y + 11), (x + 33, y + 32), color, -1)


class ModuloPesasDashboard:
    """Renderer OpenCV para el dashboard profesional del Modulo 1."""

    def __init__(self, ancho: int = ANCHO_DASHBOARD, alto: int = ALTO_DASHBOARD, assets_dir: Path = ASSETS_DIR):
        self.ancho = ancho
        self.alto = alto
        self.logo_puce = _cargar_logo(assets_dir / "logo_puce.png", 335, 92)
        self.logo_fe_alegria = _cargar_logo_fe_alegria(assets_dir / "logo_fe_alegria.png", 110, 104)
        self._bases_por_ejercicio: dict[str, np.ndarray] = {}

    def render(
        self,
        frame_camara: np.ndarray,
        ejercicio: EjercicioConfig,
        feedback: ExerciseFeedback,
        sesion: ExerciseSession,
        segundos_sesion: float,
    ) -> np.ndarray:
        lienzo = self._obtener_base(ejercicio).copy()
        self._dibujar_contenido_camara(lienzo, frame_camara)
        self._dibujar_estado_dinamico(lienzo, ejercicio, feedback)
        self._dibujar_metricas_dinamicas(lienzo, sesion)
        self._dibujar_sesion_dinamica(lienzo, sesion, segundos_sesion)
        return lienzo

    def _obtener_base(self, ejercicio: EjercicioConfig) -> np.ndarray:
        if ejercicio.tecla not in self._bases_por_ejercicio:
            lienzo = _crear_fondo(self.ancho, self.alto)
            self._dibujar_header(lienzo)
            self._dibujar_base_camara(lienzo)
            self._dibujar_base_estado(lienzo, ejercicio)
            self._dibujar_panel_ejercicios(lienzo, ejercicio)
            self._dibujar_base_metricas(lienzo)
            self._dibujar_panel_leyenda(lienzo)
            self._dibujar_base_sesion(lienzo)
            self._bases_por_ejercicio[ejercicio.tecla] = lienzo
        return self._bases_por_ejercicio[ejercicio.tecla]

    def _dibujar_header(self, lienzo: np.ndarray) -> None:
        if self.logo_puce is not None:
            _superponer_imagen(lienzo, self.logo_puce, 38, 52)
        else:
            _dibujar_texto(lienzo, "Pontificia Universidad", 40, 82, 0.62, COLOR_CYAN, 2)
            _dibujar_texto(lienzo, "Catolica del Ecuador", 40, 111, 0.62, COLOR_CYAN, 2)

        _dibujar_texto_centrado(lienzo, "PUCE MoCap - Modulo de Pesas", self.ancho // 2, 91, 1.18, COLOR_TEXTO, 2)
        _dibujar_texto_centrado(lienzo, SUBTITULO, self.ancho // 2, 128, 0.58, COLOR_TEXTO_SUAVE, 1)

        if self.logo_fe_alegria is not None:
            _superponer_imagen(lienzo, self.logo_fe_alegria, self.ancho - 292, 48)
        else:
            _dibujar_x(lienzo, (self.ancho - 242, 98), 44, COLOR_ROJO_UI)
        _dibujar_texto(lienzo, "Fe y Alegria", self.ancho - 178, 91, 0.68, COLOR_TEXTO, 2)
        _dibujar_texto(lienzo, "Ecuador", self.ancho - 178, 124, 0.68, COLOR_TEXTO, 2)

    def _dibujar_base_camara(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 24, 156, 770, 520
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)

    def _dibujar_contenido_camara(self, lienzo: np.ndarray, frame_camara: np.ndarray) -> None:
        x, y, w, h = 24, 156, 770, 520
        _pegar_imagen_redondeada(lienzo, frame_camara, x + 14, y + 14, w - 28, h - 28, 14)
        _dibujar_rectangulo_redondeado(lienzo, x + 14, y + 14, w - 28, h - 28, 14, (55, 57, 45), 1)
        _dibujar_rectangulo_redondeado(lienzo, x + 24, y + 26, 105, 34, 15, (36, 37, 38), -1)
        cv2.circle(lienzo, (x + 45, y + 43), 6, COLOR_VERDE, -1, cv2.LINE_AA)
        _dibujar_texto(lienzo, "EN VIVO", x + 61, y + 51, 0.42, COLOR_TEXTO, 2)

    def _dibujar_base_estado(self, lienzo: np.ndarray, ejercicio: EjercicioConfig) -> None:
        x, y, w, h = 815, 156, 440, 405
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        cv2.circle(lienzo, (x + 43, y + 41), 23, COLOR_CYAN_OSCURO, -1, cv2.LINE_AA)
        cv2.circle(lienzo, (x + 43, y + 41), 23, COLOR_CYAN, 1, cv2.LINE_AA)
        _dibujar_icono_modulo(lienzo, x + 28, y + 21, COLOR_CYAN)
        _dibujar_texto(lienzo, "EJERCICIO ACTUAL", x + 76, y + 39, 0.41, COLOR_TEXTO_SUAVE, 2)
        _dibujar_texto(lienzo, f"Ejercicio: {ejercicio.nombre}", x + 76, y + 88, 0.72, COLOR_TEXTO, 2)
        _dibujar_texto(lienzo, "Angulo principal", x + 76, y + 131, 0.50, COLOR_TEXTO_SUAVE, 1)

    def _dibujar_estado_dinamico(
        self, lienzo: np.ndarray, ejercicio: EjercicioConfig, feedback: ExerciseFeedback
    ) -> None:
        x, y = 815, 156
        estado_correcto = feedback.es_correcto
        color_estado = COLOR_VERDE if estado_correcto else COLOR_ROJO_UI
        color_estado_oscuro = COLOR_VERDE_OSCURO if estado_correcto else COLOR_ROJO_OSCURO
        etiqueta_estado = "VERDE / CORRECTO" if estado_correcto else "ROJO / CORREGIR"

        valor_angulo = feedback.angulos.get(ejercicio.angulo_principal)
        self._dibujar_angulo_principal(lienzo, x + 76, y + 199, valor_angulo, color_estado)

        chip_x, chip_y, chip_w, chip_h = x + 70, y + 221, 330, 58
        _dibujar_rectangulo_redondeado(lienzo, chip_x, chip_y, chip_w, chip_h, 10, color_estado_oscuro, -1)
        _dibujar_rectangulo_redondeado(lienzo, chip_x, chip_y, chip_w, chip_h, 10, color_estado, 1)
        if estado_correcto:
            _dibujar_check(lienzo, (x + 104, y + 250), 16, color_estado)
        else:
            _dibujar_x(lienzo, (x + 104, y + 250), 16, color_estado)
        _dibujar_texto_centrado(lienzo, etiqueta_estado, chip_x + chip_w // 2 + 14, y + 260, 0.54, COLOR_TEXTO, 2)

        mensaje = feedback.mensajes[0] if feedback.mensajes else "Sesion iniciada."
        lineas = limitar_lineas_texto(mensaje, 332, 0.46, 1, 3)
        if estado_correcto:
            _dibujar_check(lienzo, (x + 52, y + 326), 15, (42, 168, 70))
        else:
            _dibujar_x(lienzo, (x + 52, y + 326), 15, color_estado)
        for indice, linea in enumerate(lineas):
            _dibujar_texto(lienzo, linea, x + 76, y + 316 + indice * 28, 0.46, COLOR_TEXTO, 1)

    def _dibujar_base_metricas(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 815, 580, 440, 108
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 15)
        ancho_columna = w // 3
        for divisor in (1, 2):
            cv2.line(lienzo, (x + divisor * ancho_columna, y + 12), (x + divisor * ancho_columna, y + h - 12), COLOR_BORDE, 1)

        metricas = [
            ("REPS", _dibujar_icono_reps, COLOR_TEXTO_MUTED),
            ("CORRECTO", _dibujar_icono_target, COLOR_VERDE),
            ("FRAMES", _dibujar_icono_frames, COLOR_TEXTO_MUTED),
        ]
        for indice, (titulo, icono, color) in enumerate(metricas):
            col_x = x + indice * ancho_columna
            icono(lienzo, col_x + 24, y + 13, color)
            _dibujar_texto(lienzo, titulo, col_x + 67, y + 34, 0.36, COLOR_TEXTO_SUAVE, 1)

    def _dibujar_metricas_dinamicas(self, lienzo: np.ndarray, sesion: ExerciseSession) -> None:
        x, y, w = 815, 580, 440
        ancho_columna = w // 3
        porcentaje = sesion.porcentaje_correcto
        metricas = [
            (str(sesion.repeticiones), COLOR_TEXTO),
            (f"{porcentaje:.0f}%", COLOR_VERDE),
            (str(sesion.total_frames), COLOR_TEXTO),
        ]
        for indice, (valor, color) in enumerate(metricas):
            col_x = x + indice * ancho_columna
            _dibujar_texto_centrado(lienzo, valor, col_x + ancho_columna // 2, y + 78, 0.88, color, 2)
        _dibujar_barra(lienzo, x + ancho_columna + 30, y + 88, ancho_columna - 60, 9, porcentaje / 100.0, COLOR_VERDE)

    def _dibujar_base_sesion(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 745, 708, 830, 148
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 16)
        _dibujar_icono_chart(lienzo, x + 28, y + 18, COLOR_TEXTO_MUTED)
        _dibujar_texto(lienzo, "SESION EN CURSO", x + 72, y + 38, 0.43, COLOR_TEXTO_SUAVE, 2)

        titulos = ["DURACION", "PORCENTAJE CORRECTO", "CALIDAD GLOBAL"]
        for indice, titulo in enumerate(titulos):
            col_x = x + 48 + indice * 260
            if indice > 0:
                cv2.line(lienzo, (col_x - 35, y + 62), (col_x - 35, y + h - 26), COLOR_BORDE, 1)
            _dibujar_texto(lienzo, titulo, col_x + 54, y + 80, 0.38, COLOR_TEXTO_SUAVE, 1)

    def _dibujar_sesion_dinamica(self, lienzo: np.ndarray, sesion: ExerciseSession, segundos_sesion: float) -> None:
        x, y = 745, 708
        porcentaje = sesion.porcentaje_correcto
        calidad = describir_calidad_global(porcentaje, sesion.total_frames)
        columnas = [
            (formatear_duracion(segundos_sesion), COLOR_AZUL, min(1.0, segundos_sesion / 900.0), _dibujar_icono_reloj),
            (f"{porcentaje:.0f}%", COLOR_VERDE, porcentaje / 100.0, _dibujar_icono_target),
            (calidad, COLOR_VERDE if porcentaje >= 75.0 else COLOR_AZUL, porcentaje / 100.0, None),
        ]
        ancho_columna = 245
        for indice, (valor, color, progreso, icono) in enumerate(columnas):
            col_x = x + 48 + indice * 260
            if icono is None:
                _dibujar_check(lienzo, (col_x + 20, y + 84), 15, color)
            else:
                icono(lienzo, col_x, y + 63, color)
            _dibujar_texto(lienzo, valor, col_x + 54, y + 108, 0.52, COLOR_TEXTO, 2)
            _dibujar_barra(lienzo, col_x, y + 122, ancho_columna - 55, 9, progreso, color)

    def _dibujar_panel_camara(self, lienzo: np.ndarray, frame_camara: np.ndarray) -> None:
        x, y, w, h = 24, 156, 770, 520
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        _pegar_imagen_redondeada(lienzo, frame_camara, x + 14, y + 14, w - 28, h - 28, 14)
        _dibujar_rectangulo_redondeado(lienzo, x + 14, y + 14, w - 28, h - 28, 14, (55, 57, 45), 1)
        _dibujar_sombra(lienzo, x + 22, y + 24, 110, 36, 16, (0, 0, 0), 0.40, 19)
        _dibujar_rectangulo_redondeado(lienzo, x + 24, y + 26, 105, 34, 15, (36, 37, 38), -1)
        cv2.circle(lienzo, (x + 45, y + 43), 6, COLOR_VERDE, -1, cv2.LINE_AA)
        _dibujar_texto(lienzo, "EN VIVO", x + 61, y + 51, 0.42, COLOR_TEXTO, 2)

    def _dibujar_panel_estado(self, lienzo: np.ndarray, ejercicio: EjercicioConfig, feedback: ExerciseFeedback) -> None:
        x, y, w, h = 815, 156, 440, 405
        estado_correcto = feedback.es_correcto
        color_estado = COLOR_VERDE if estado_correcto else COLOR_ROJO_UI
        color_estado_oscuro = COLOR_VERDE_OSCURO if estado_correcto else COLOR_ROJO_OSCURO
        etiqueta_estado = "VERDE / CORRECTO" if estado_correcto else "ROJO / CORREGIR"

        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        cv2.circle(lienzo, (x + 43, y + 41), 23, COLOR_CYAN_OSCURO, -1, cv2.LINE_AA)
        cv2.circle(lienzo, (x + 43, y + 41), 23, COLOR_CYAN, 1, cv2.LINE_AA)
        _dibujar_icono_modulo(lienzo, x + 28, y + 21, COLOR_CYAN)
        _dibujar_texto(lienzo, "EJERCICIO ACTUAL", x + 76, y + 39, 0.41, COLOR_TEXTO_SUAVE, 2)
        _dibujar_texto(lienzo, f"Ejercicio: {ejercicio.nombre}", x + 76, y + 88, 0.72, COLOR_TEXTO, 2)

        _dibujar_texto(lienzo, "Angulo principal", x + 76, y + 131, 0.50, COLOR_TEXTO_SUAVE, 1)
        valor_angulo = feedback.angulos.get(ejercicio.angulo_principal)
        self._dibujar_angulo_principal(lienzo, x + 76, y + 199, valor_angulo, color_estado)

        _dibujar_sombra(lienzo, x + 68, y + 222, 334, 56, 10, color_estado, 0.12, 21)
        chip_x, chip_y, chip_w, chip_h = x + 70, y + 221, 330, 58
        _dibujar_rectangulo_redondeado(lienzo, chip_x, chip_y, chip_w, chip_h, 10, color_estado_oscuro, -1)
        _dibujar_rectangulo_redondeado(lienzo, chip_x, chip_y, chip_w, chip_h, 10, color_estado, 1)
        if estado_correcto:
            _dibujar_check(lienzo, (x + 104, y + 250), 16, color_estado)
        else:
            _dibujar_x(lienzo, (x + 104, y + 250), 16, color_estado)
        _dibujar_texto_centrado(lienzo, etiqueta_estado, chip_x + chip_w // 2 + 14, y + 260, 0.54, COLOR_TEXTO, 2)

        mensaje = feedback.mensajes[0] if feedback.mensajes else "Sesion iniciada."
        lineas = limitar_lineas_texto(mensaje, 332, 0.46, 1, 3)
        if estado_correcto:
            _dibujar_check(lienzo, (x + 52, y + 326), 15, (42, 168, 70))
        else:
            _dibujar_x(lienzo, (x + 52, y + 326), 15, color_estado)
        for indice, linea in enumerate(lineas):
            _dibujar_texto(lienzo, linea, x + 76, y + 316 + indice * 28, 0.46, COLOR_TEXTO, 1)

    def _dibujar_angulo_principal(
        self, lienzo: np.ndarray, x: int, y_base: int, valor: float | None, color: tuple[int, int, int]
    ) -> None:
        if valor is None:
            _dibujar_texto(lienzo, "N/D", x, y_base, 1.62, color, 1)
            return

        texto = f"{valor:.0f}"
        escala = 1.86
        grosor = 2
        _dibujar_texto(lienzo, texto, x, y_base, escala, color, grosor)
        ancho_texto, alto_texto = _medir_texto(texto, escala, grosor)
        cv2.circle(lienzo, (x + ancho_texto + 18, y_base - alto_texto + 18), 8, color, 3, cv2.LINE_AA)

    def _dibujar_panel_ejercicios(self, lienzo: np.ndarray, ejercicio: EjercicioConfig) -> None:
        x, y, w, h = 1275, 156, 300, 450
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 18)
        _dibujar_icono_chart(lienzo, x + 28, y + 20, COLOR_TEXTO_MUTED)
        _dibujar_texto(lienzo, "EJERCICIOS", x + 72, y + 40, 0.43, COLOR_TEXTO_SUAVE, 2)

        for indice, config in enumerate(EJERCICIOS.values()):
            boton_y = y + 66 + indice * 72
            seleccionado = config.tecla == ejercicio.tecla
            relleno = (70, 82, 47) if seleccionado else COLOR_TARJETA_SUAVE
            borde = COLOR_CYAN if seleccionado else (70, 82, 66)
            if seleccionado:
                _dibujar_sombra(lienzo, x + 20, boton_y, w - 40, 58, 9, COLOR_CYAN, 0.12, 21)
            _dibujar_rectangulo_redondeado(lienzo, x + 20, boton_y, w - 40, 58, 9, relleno, -1)
            _dibujar_rectangulo_redondeado(lienzo, x + 20, boton_y, w - 40, 58, 9, borde, 2 if seleccionado else 1)
            icon_color = COLOR_TEXTO if seleccionado else COLOR_TEXTO_SUAVE
            if config.nombre == "Sentadilla":
                _dibujar_icono_sentadilla(lienzo, x + 34, boton_y + 8, icon_color)
            else:
                _dibujar_icono_barra(lienzo, x + 32, boton_y + 8, icon_color)
            _dibujar_texto(lienzo, config.tecla, x + 82, boton_y + 37, 0.50, COLOR_TEXTO, 2)
            _dibujar_texto(lienzo, config.nombre, x + 112, boton_y + 37, 0.48, COLOR_TEXTO, 2)

        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 304, w - 40, 58, 9, COLOR_TARJETA_SUAVE, -1)
        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 304, w - 40, 58, 9, COLOR_AZUL, 1)
        _dibujar_icono_refresh(lienzo, x + 37, y + 314, COLOR_AZUL)
        _dibujar_texto(lienzo, "Reiniciar", x + 96, y + 342, 0.50, (235, 182, 118), 2)

        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 374, w - 40, 58, 9, (42, 31, 48), -1)
        _dibujar_rectangulo_redondeado(lienzo, x + 20, y + 374, w - 40, 58, 9, COLOR_ROJO_UI, 1)
        _dibujar_icono_power(lienzo, x + 37, y + 383, COLOR_ROJO_UI)
        _dibujar_texto(lienzo, "Salir", x + 96, y + 412, 0.50, COLOR_ROJO_UI, 2)

    def _dibujar_panel_metricas(self, lienzo: np.ndarray, sesion: ExerciseSession) -> None:
        x, y, w, h = 815, 580, 440, 108
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 15)
        ancho_columna = w // 3
        for divisor in (1, 2):
            cv2.line(lienzo, (x + divisor * ancho_columna, y + 12), (x + divisor * ancho_columna, y + h - 12), COLOR_BORDE, 1)

        porcentaje = sesion.porcentaje_correcto
        metricas = [
            ("REPS", str(sesion.repeticiones), COLOR_TEXTO, _dibujar_icono_reps),
            ("CORRECTO", f"{porcentaje:.0f}%", COLOR_VERDE, _dibujar_icono_target),
            ("FRAMES", str(sesion.total_frames), COLOR_TEXTO, _dibujar_icono_frames),
        ]
        for indice, (titulo, valor, color, icono) in enumerate(metricas):
            col_x = x + indice * ancho_columna
            label_x = col_x + 67
            icono(lienzo, col_x + 24, y + 13, COLOR_VERDE if indice == 1 else COLOR_TEXTO_MUTED)
            _dibujar_texto(lienzo, titulo, label_x, y + 34, 0.36, COLOR_TEXTO_SUAVE, 1)
            _dibujar_texto_centrado(lienzo, valor, col_x + ancho_columna // 2, y + 78, 0.88, color, 2)
        _dibujar_barra(lienzo, x + ancho_columna + 30, y + 88, ancho_columna - 60, 9, porcentaje / 100.0, COLOR_VERDE)

    def _dibujar_panel_leyenda(self, lienzo: np.ndarray) -> None:
        x, y, w, h = 24, 708, 700, 148
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 16)
        _dibujar_icono_chart(lienzo, x + 28, y + 18, COLOR_TEXTO_MUTED)
        _dibujar_texto(lienzo, "LEYENDA DE ESTADO", x + 72, y + 38, 0.43, COLOR_TEXTO_SUAVE, 2)

        self._dibujar_tarjeta_leyenda(lienzo, x + 34, y + 58, 275, "VERDE = CORRECTO", "Ejercicio ejecutado con buena tecnica.", True)
        self._dibujar_tarjeta_leyenda(
            lienzo, x + 330, y + 58, 330, "ROJO = CORREGIR POSTURA", "Ajusta la postura y vuelve a intentar.", False
        )

    def _dibujar_tarjeta_leyenda(
        self, lienzo: np.ndarray, x: int, y: int, w: int, titulo: str, detalle: str, correcto: bool
    ) -> None:
        color = COLOR_VERDE if correcto else COLOR_ROJO_UI
        fondo = COLOR_VERDE_OSCURO if correcto else COLOR_ROJO_OSCURO
        _dibujar_sombra(lienzo, x, y + 2, w, 80, 10, color, 0.08, 17)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, 80, 10, fondo, -1)
        _dibujar_rectangulo_redondeado(lienzo, x, y, w, 80, 10, color, 1)
        if correcto:
            _dibujar_check(lienzo, (x + 36, y + 38), 18, color)
        else:
            _dibujar_x(lienzo, (x + 36, y + 38), 18, color)
        _dibujar_texto(lienzo, titulo, x + 72, y + 31, 0.41, color, 2)
        for indice, linea in enumerate(dividir_texto(detalle, w - 90, 0.38, 1)[:2]):
            _dibujar_texto(lienzo, linea, x + 72, y + 55 + indice * 20, 0.38, COLOR_TEXTO, 1)

    def _dibujar_panel_sesion(self, lienzo: np.ndarray, sesion: ExerciseSession, segundos_sesion: float) -> None:
        x, y, w, h = 745, 708, 830, 148
        _dibujar_tarjeta_base(lienzo, x, y, w, h, 16)
        _dibujar_icono_chart(lienzo, x + 28, y + 18, COLOR_TEXTO_MUTED)
        _dibujar_texto(lienzo, "SESION EN CURSO", x + 72, y + 38, 0.43, COLOR_TEXTO_SUAVE, 2)

        porcentaje = sesion.porcentaje_correcto
        calidad = describir_calidad_global(porcentaje, sesion.total_frames)
        columnas = [
            ("DURACION", formatear_duracion(segundos_sesion), COLOR_AZUL, min(1.0, segundos_sesion / 900.0), _dibujar_icono_reloj),
            ("PORCENTAJE CORRECTO", f"{porcentaje:.0f}%", COLOR_VERDE, porcentaje / 100.0, _dibujar_icono_target),
            ("CALIDAD GLOBAL", calidad, COLOR_VERDE if porcentaje >= 75.0 else COLOR_AZUL, porcentaje / 100.0, None),
        ]
        ancho_columna = 245
        for indice, (titulo, valor, color, progreso, icono) in enumerate(columnas):
            col_x = x + 48 + indice * 260
            if indice > 0:
                cv2.line(lienzo, (col_x - 35, y + 62), (col_x - 35, y + h - 26), COLOR_BORDE, 1)
            if icono is None:
                _dibujar_check(lienzo, (col_x + 20, y + 84), 15, color)
            else:
                icono(lienzo, col_x, y + 63, color)
            _dibujar_texto(lienzo, titulo, col_x + 54, y + 80, 0.38, COLOR_TEXTO_SUAVE, 1)
            _dibujar_texto(lienzo, valor, col_x + 54, y + 108, 0.52, COLOR_TEXTO, 2)
            _dibujar_barra(lienzo, col_x, y + 122, ancho_columna - 55, 9, progreso, color)


def _reiniciar_sesion(ejercicio: EjercicioConfig) -> tuple[ExerciseSession, float]:
    return ExerciseSession(ejercicio.nombre), time.monotonic()


def main() -> None:
    """Ejecuta la interfaz final del Modulo 1 con camara, pose y reporte CSV."""
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

    dashboard = ModuloPesasDashboard()
    ejercicio = EJERCICIOS["1"]
    sesion, inicio_sesion = _reiniciar_sesion(ejercicio)

    cv2.namedWindow(VENTANA_TITULO, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(VENTANA_TITULO, dashboard.ancho, dashboard.alto)

    print("PUCE MoCap - Modulo de Pesas iniciado.")
    print("Teclas: 1 Sentadilla | 2 Press hombro | 3 Peso muerto | r Reiniciar | q Salir")

    with mp_pose.Pose(model_complexity=1, min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer un frame de la camara.")
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultado = pose.process(rgb)

            frame_visual = frame.copy()
            if resultado.pose_landmarks:
                mp_drawing.draw_landmarks(
                    frame_visual,
                    resultado.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=landmark_spec,
                    connection_drawing_spec=connection_spec,
                )
                esqueleto = mediapipe_a_esqueleto_3d(resultado.pose_landmarks)
                feedback = evaluar_esqueleto(ejercicio, esqueleto)
            else:
                feedback = _feedback_incompleto(ejercicio.nombre)

            if feedback.angulos:
                sesion.registrar_feedback(feedback)

            segundos_sesion = time.monotonic() - inicio_sesion
            lienzo = dashboard.render(frame_visual, ejercicio, feedback, sesion, segundos_sesion)
            cv2.imshow(VENTANA_TITULO, lienzo)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                break
            if tecla in (ord("1"), ord("2"), ord("3")):
                ejercicio = EJERCICIOS[chr(tecla)]
                sesion, inicio_sesion = _reiniciar_sesion(ejercicio)
            elif tecla == ord("r"):
                sesion, inicio_sesion = _reiniciar_sesion(ejercicio)

            if cv2.getWindowProperty(VENTANA_TITULO, cv2.WND_PROP_VISIBLE) < 1:
                break

    cap.release()
    cv2.destroyAllWindows()
    REPORTE_LIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    generar_reporte_csv(sesion.exportar_resumen(), REPORTE_LIVE_PATH)
    print(f"Reporte CSV generado: {REPORTE_LIVE_PATH}")


if __name__ == "__main__":
    main()
