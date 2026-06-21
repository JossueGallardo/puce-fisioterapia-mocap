"""Análisis de ejercicios terapéuticos con rangos configurables."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from puce_mocap.angle_utils import calcular_angulo, calcular_angulo_vectores
from puce_mocap.rehab_profiles import EJERCICIOS_REHABILITACION


ESTADO_DENTRO_RANGO = "DENTRO_DEL_RANGO"
ESTADO_FUERA_RANGO = "FUERA_DEL_RANGO"
ESTADO_POSTURA_INCOMPLETA = "POSTURA_INCOMPLETA"

COLOR_VERDE = "verde"
COLOR_AMARILLO = "amarillo"
COLOR_ROJO = "rojo"

MENSAJE_DENTRO_RANGO = "Dentro del rango terapéutico."
MENSAJE_FUERA_RANGO = "Fuera del rango indicado para este perfil."
MENSAJE_POSTURA_INCOMPLETA = "No se detecta postura completa."
MENSAJE_REVISAR = "Revisar con fisioterapeuta."

Punto = Sequence[float]
Esqueleto = Mapping[str, Punto]


@dataclass(frozen=True)
class RehabAnalysisResult:
    """Resultado de evaluar un fotograma de rehabilitación."""

    ejercicio: str
    estado: str
    color: str
    angulo_actual: float | None
    angulo_minimo: float
    angulo_maximo: float
    dentro_rango: bool
    mensajes: list[str] = field(default_factory=list)
    fase: str = "transicion"
    forma_correcta: bool | None = None
    repeticion_completada: bool = False

    @property
    def frame_valido(self) -> bool:
        return self.estado != ESTADO_POSTURA_INCOMPLETA

    def to_dict(self) -> dict[str, Any]:
        return {
            "ejercicio": self.ejercicio,
            "estado": self.estado,
            "color": self.color,
            "angulo_actual": self.angulo_actual,
            "angulo_minimo": self.angulo_minimo,
            "angulo_maximo": self.angulo_maximo,
            "dentro_rango": self.dentro_rango,
            "mensajes": list(self.mensajes),
            "frame_valido": self.frame_valido,
            "fase": self.fase,
            "forma_correcta": self.forma_correcta,
            "repeticion_completada": self.repeticion_completada,
        }


def _normalizar_clave(nombre: str) -> str:
    return nombre.replace("-", "_").replace(" ", "_").lower()


def _normalizar_lado(lado: str) -> str:
    lado_normalizado = lado.lower().strip()
    if lado_normalizado in {"right", "derecho", "derecha", "d"}:
        return "right"
    if lado_normalizado in {"left", "izquierdo", "izquierda", "i"}:
        return "left"
    raise ValueError("El lado debe ser right/left o derecho/izquierdo.")


def _indice(esqueleto: Esqueleto) -> dict[str, tuple[str, Punto]]:
    return {_normalizar_clave(nombre): (nombre, valor) for nombre, valor in esqueleto.items()}


def _convertir_punto(valor: Punto, nombre: str) -> np.ndarray:
    punto = np.asarray(valor, dtype=float)
    if punto.shape not in {(2,), (3,)}:
        raise ValueError(f"{nombre} debe tener 2 o 3 coordenadas.")
    return punto


def _punto(indice: Mapping[str, tuple[str, Punto]], *nombres: str) -> np.ndarray:
    for nombre in nombres:
        clave = _normalizar_clave(nombre)
        if clave in indice:
            nombre_original, valor = indice[clave]
            return _convertir_punto(valor, nombre_original)
    raise ValueError("No se encontró una articulación requerida.")


def _punto_lado(indice: Mapping[str, tuple[str, Punto]], lado: str, articulacion: str) -> np.ndarray:
    alias = {
        "shoulder": ("shoulder", "hombro"),
        "elbow": ("elbow", "codo"),
        "wrist": ("wrist", "muneca", "muñeca"),
        "index": ("index", "hand", "mano", "dedo_indice"),
        "pinky": ("pinky", "menique", "meñique"),
        "hip": ("hip", "cadera"),
        "knee": ("knee", "rodilla"),
        "ankle": ("ankle", "tobillo"),
        "foot": ("foot", "foot_index", "toe", "pie", "punta_pie"),
    }
    candidatos: list[str] = []
    for base in alias[articulacion]:
        candidatos.extend((f"{lado}_{base}", f"{base}_{lado}"))
    return _punto(indice, *candidatos)


def _vertical_abajo(punto: np.ndarray) -> np.ndarray:
    if punto.shape == (2,):
        return np.array([0.0, -1.0])
    return np.array([0.0, -1.0, 0.0])


class WristRotationCalibrator:
    """Estima pronación/supinación relativa alrededor del eje del antebrazo."""

    def __init__(self) -> None:
        self._referencia: np.ndarray | None = None

    @property
    def calibrado(self) -> bool:
        return self._referencia is not None

    @staticmethod
    def _vector_palmar(esqueleto: Esqueleto, lado: str) -> tuple[np.ndarray, np.ndarray]:
        indice = _indice(esqueleto)
        codo = _punto_lado(indice, lado, "elbow")
        muneca = _punto_lado(indice, lado, "wrist")
        dedo_indice = _punto_lado(indice, lado, "index")
        menique = _punto_lado(indice, lado, "pinky")
        antebrazo = muneca - codo
        norma_antebrazo = float(np.linalg.norm(antebrazo))
        if norma_antebrazo == 0.0:
            raise ValueError("No se puede determinar el eje del antebrazo.")
        eje = antebrazo / norma_antebrazo
        vector_mano = ((dedo_indice + menique) / 2.0) - muneca
        proyectado = vector_mano - float(np.dot(vector_mano, eje)) * eje
        norma = float(np.linalg.norm(proyectado))
        if norma == 0.0:
            raise ValueError("No se puede determinar la orientación de la mano.")
        return proyectado / norma, eje

    def calibrar(self, esqueleto: Esqueleto, lado: str = "right") -> None:
        self._referencia, _ = self._vector_palmar(esqueleto, _normalizar_lado(lado))

    def medir(self, esqueleto: Esqueleto, lado: str = "right") -> float:
        if self._referencia is None:
            raise ValueError("La rotación de muñeca requiere calibración neutral.")
        actual, eje = self._vector_palmar(esqueleto, _normalizar_lado(lado))
        seno = float(np.dot(eje, np.cross(self._referencia, actual)))
        coseno = float(np.clip(np.dot(self._referencia, actual), -1.0, 1.0))
        return float(abs(np.degrees(np.arctan2(seno, coseno))))


def _calcular_angulo_ejercicio(
    nombre: str,
    esqueleto: Esqueleto,
    lado: str,
    calibrador_muneca: WristRotationCalibrator | None = None,
) -> tuple[float, list[str]]:
    indice = _indice(esqueleto)

    if nombre == "flexion_codo":
        hombro = _punto_lado(indice, lado, "shoulder")
        codo = _punto_lado(indice, lado, "elbow")
        muneca = _punto_lado(indice, lado, "wrist")
        return calcular_angulo(hombro, codo, muneca), []

    if nombre == "abduccion_hombro":
        cadera = _punto_lado(indice, lado, "hip")
        hombro = _punto_lado(indice, lado, "shoulder")
        codo = _punto_lado(indice, lado, "elbow")
        return calcular_angulo(cadera, hombro, codo), []

    if nombre == "rotacion_muneca":
        if calibrador_muneca is None or not calibrador_muneca.calibrado:
            raise ValueError("La rotación de muñeca requiere calibración neutral.")
        return calibrador_muneca.medir(esqueleto, lado), ["Rotación relativa a la calibración neutral."]

    if nombre == "extension_rodilla":
        cadera = _punto_lado(indice, lado, "hip")
        rodilla = _punto_lado(indice, lado, "knee")
        tobillo = _punto_lado(indice, lado, "ankle")
        return calcular_angulo(cadera, rodilla, tobillo), []

    if nombre == "dorsiflexion_tobillo":
        rodilla = _punto_lado(indice, lado, "knee")
        tobillo = _punto_lado(indice, lado, "ankle")
        pie = _punto_lado(indice, lado, "foot")
        angulo_crudo = calcular_angulo(rodilla, tobillo, pie)
        return abs(90.0 - angulo_crudo), []

    if nombre == "elevacion_pierna_recta":
        cadera = _punto_lado(indice, lado, "hip")
        rodilla = _punto_lado(indice, lado, "knee")
        tobillo = _punto_lado(indice, lado, "ankle")
        elevacion = calcular_angulo_vectores(rodilla - cadera, _vertical_abajo(cadera))
        angulo_rodilla = calcular_angulo(cadera, rodilla, tobillo)
        mensajes = [] if angulo_rodilla >= 160.0 else ["Mantener la rodilla extendida durante la elevación."]
        return elevacion, mensajes

    raise ValueError(f"Ejercicio de rehabilitación no soportado: {nombre}.")


def evaluar_ejercicio_rehabilitacion(
    nombre_ejercicio: str,
    esqueleto: Esqueleto,
    perfil: Mapping[str, Any],
    calibrador_muneca: WristRotationCalibrator | None = None,
) -> RehabAnalysisResult:
    """Evalúa un ejercicio usando el rango configurado en el perfil."""
    nombre = _normalizar_clave(nombre_ejercicio)
    if nombre not in EJERCICIOS_REHABILITACION:
        raise ValueError(f"Ejercicio de rehabilitación no soportado: {nombre_ejercicio}.")

    ejercicios = perfil.get("ejercicios")
    if not isinstance(ejercicios, Mapping) or nombre not in ejercicios:
        raise ValueError(f"El perfil no tiene configurado el ejercicio {nombre}.")

    configuracion = ejercicios[nombre]
    rango_objetivo = configuracion.get("rango_objetivo")
    rango_inicio = configuracion.get("rango_inicio")
    if not isinstance(rango_objetivo, Mapping):
        rango_objetivo = {
            "minimo": configuracion["angulo_minimo"],
            "maximo": configuracion["angulo_maximo"],
        }
    if not isinstance(rango_inicio, Mapping):
        from puce_mocap.rehab_profiles import RANGOS_INICIO_PREDETERMINADOS

        inicio_min, inicio_max = RANGOS_INICIO_PREDETERMINADOS[nombre]
        rango_inicio = {"minimo": inicio_min, "maximo": inicio_max}
    minimo = float(rango_objetivo["minimo"])
    maximo = float(rango_objetivo["maximo"])
    lado = _normalizar_lado(str(configuracion.get("lado", "right")))

    try:
        angulo_actual, mensajes_adicionales = _calcular_angulo_ejercicio(
            nombre, esqueleto, lado, calibrador_muneca
        )
    except (KeyError, ValueError):
        return RehabAnalysisResult(
            ejercicio=nombre,
            estado=ESTADO_POSTURA_INCOMPLETA,
            color=COLOR_ROJO,
            angulo_actual=None,
            angulo_minimo=minimo,
            angulo_maximo=maximo,
            dentro_rango=False,
            mensajes=[MENSAJE_POSTURA_INCOMPLETA],
        )

    dentro_rango = minimo <= angulo_actual <= maximo
    en_inicio = float(rango_inicio["minimo"]) <= angulo_actual <= float(rango_inicio["maximo"])
    fase = "objetivo" if dentro_rango else "inicio" if en_inicio else "transicion"
    forma_correcta: bool | None = True if dentro_rango else None
    if nombre == "elevacion_pierna_recta" and mensajes_adicionales:
        dentro_rango = False
        fase = "transicion"
        forma_correcta = False

    if dentro_rango:
        estado = ESTADO_DENTRO_RANGO
        color = COLOR_VERDE
        mensajes = [MENSAJE_DENTRO_RANGO]
    else:
        estado = ESTADO_FUERA_RANGO
        color = COLOR_AMARILLO
        mensajes = [MENSAJE_FUERA_RANGO, MENSAJE_REVISAR]

    mensajes.extend(mensajes_adicionales)
    return RehabAnalysisResult(
        ejercicio=nombre,
        estado=estado,
        color=color,
        angulo_actual=float(angulo_actual),
        angulo_minimo=minimo,
        angulo_maximo=maximo,
        dentro_rango=dentro_rango,
        mensajes=mensajes,
        fase=fase,
        forma_correcta=forma_correcta,
    )
