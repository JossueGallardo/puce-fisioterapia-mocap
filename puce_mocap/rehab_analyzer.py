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
MENSAJE_POSTURA_INCOMPLETA = "No se detectan todas las articulaciones necesarias."
MENSAJE_REVISAR = "Revisar con fisioterapeuta."
CONFIANZA_MINIMA_ARTICULACION = 0.65

ARTICULACIONES_REQUERIDAS = {
    "flexion_codo": ("shoulder", "elbow", "wrist"),
    "abduccion_hombro": ("hip", "shoulder", "elbow"),
    "rotacion_muneca": ("elbow", "wrist", "index", "pinky"),
    "extension_rodilla": ("hip", "knee", "ankle"),
    "dorsiflexion_tobillo": ("knee", "ankle", "foot"),
    "elevacion_pierna_recta": ("hip", "knee", "ankle"),
}

NOMBRES_ARTICULACIONES = {
    "shoulder": "hombro",
    "elbow": "codo",
    "wrist": "muñeca",
    "index": "dedo índice",
    "pinky": "meñique",
    "hip": "cadera",
    "knee": "rodilla",
    "ankle": "tobillo",
    "foot": "punta del pie",
}

EJERCICIOS_COMPATIBLES_SENTADO = {
    "flexion_codo",
    "abduccion_hombro",
    "rotacion_muneca",
    "extension_rodilla",
    "dorsiflexion_tobillo",
}

ORIENTACION_RECOMENDADA = {
    "flexion_codo": "frontal",
    "abduccion_hombro": "frontal",
    "rotacion_muneca": "frontal",
    "extension_rodilla": "lateral",
    "dorsiflexion_tobillo": "lateral",
    "elevacion_pierna_recta": "lateral",
}

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
    lado_evaluado: str | None = None

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
            "lado_evaluado": self.lado_evaluado,
        }


def _normalizar_clave(nombre: str) -> str:
    return nombre.replace("-", "_").replace(" ", "_").lower()


def _normalizar_lado(lado: str) -> str:
    lado_normalizado = lado.lower().strip()
    if lado_normalizado in {"auto", "automatico", "automático", "mejor_visible"}:
        return "auto"
    if lado_normalizado in {"right", "derecho", "derecha", "d"}:
        return "right"
    if lado_normalizado in {"left", "izquierdo", "izquierda", "i"}:
        return "left"
    raise ValueError("El lado debe ser auto, right/left o automático/derecho/izquierdo.")


def _indice(esqueleto: Esqueleto) -> dict[str, tuple[str, Punto]]:
    return {_normalizar_clave(nombre): (nombre, valor) for nombre, valor in esqueleto.items()}


def _convertir_punto(valor: Punto, nombre: str) -> np.ndarray:
    punto = np.asarray(valor, dtype=float)
    if punto.shape not in {(2,), (3,)}:
        raise ValueError(f"{nombre} debe tener 2 o 3 coordenadas.")
    if not np.all(np.isfinite(punto)):
        raise ValueError(f"{nombre} contiene coordenadas no válidas.")
    return punto


def _punto(indice: Mapping[str, tuple[str, Punto]], *nombres: str) -> np.ndarray:
    for nombre in nombres:
        clave = _normalizar_clave(nombre)
        if clave in indice:
            nombre_original, valor = indice[clave]
            return _convertir_punto(valor, nombre_original)
    raise ValueError("No se encontró una articulación requerida.")


def _claves_lado(lado: str, articulacion: str) -> tuple[str, ...]:
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
    return tuple(candidatos)


def _punto_lado(indice: Mapping[str, tuple[str, Punto]], lado: str, articulacion: str) -> np.ndarray:
    return _punto(indice, *_claves_lado(lado, articulacion))


def _mensaje_visibilidad(nombre: str, lado: str, automatico: bool = False) -> str:
    articulaciones = [NOMBRES_ARTICULACIONES[item] for item in ARTICULACIONES_REQUERIDAS[nombre]]
    if len(articulaciones) > 1:
        lista = ", ".join(articulaciones[:-1]) + f" y {articulaciones[-1]}"
    else:
        lista = articulaciones[0]
    lado_texto = (
        "de al menos una extremidad"
        if automatico
        else f"del lado {'derecho' if lado == 'right' else 'izquierdo'}"
    )
    sentado = " Puede realizarse sentado." if nombre in EJERCICIOS_COMPATIBLES_SENTADO else ""
    return f"Mantenga visibles {lista} {lado_texto}.{sentado}"


def _articulaciones_disponibles(
    nombre: str,
    esqueleto: Esqueleto,
    lado: str,
    confianza: Mapping[str, float] | None,
) -> bool:
    indice = _indice(esqueleto)
    usar_confianza = bool(confianza)
    confianza_normalizada = (
        {_normalizar_clave(clave): float(valor) for clave, valor in confianza.items()}
        if usar_confianza and confianza is not None
        else {}
    )
    for articulacion in ARTICULACIONES_REQUERIDAS[nombre]:
        encontrada = False
        for candidata in _claves_lado(lado, articulacion):
            clave = _normalizar_clave(candidata)
            if clave not in indice:
                continue
            nombre_original, valor = indice[clave]
            try:
                _convertir_punto(valor, nombre_original)
            except ValueError:
                continue
            if usar_confianza and confianza_normalizada.get(clave, 0.0) < CONFIANZA_MINIMA_ARTICULACION:
                continue
            encontrada = True
            break
        if not encontrada:
            return False
    return True


def _confianza_lado(
    nombre: str,
    esqueleto: Esqueleto,
    lado: str,
    confianza: Mapping[str, float] | None,
) -> float:
    if not _articulaciones_disponibles(nombre, esqueleto, lado, confianza):
        return -1.0
    if not confianza:
        return 1.0
    confianza_normalizada = {_normalizar_clave(clave): float(valor) for clave, valor in confianza.items()}
    valores = []
    for articulacion in ARTICULACIONES_REQUERIDAS[nombre]:
        valores.append(
            max(
                confianza_normalizada.get(_normalizar_clave(clave), 0.0)
                for clave in _claves_lado(lado, articulacion)
            )
        )
    return float(min(valores))


def resolver_lado_ejercicio(
    nombre_ejercicio: str,
    esqueleto: Esqueleto,
    lado_configurado: str,
    confianza: Mapping[str, float] | None = None,
    lado_preferido: str | None = None,
) -> str:
    """Resuelve la extremidad mejor visible sin exigir una vista lateral."""
    nombre = _normalizar_clave(nombre_ejercicio)
    configurado = _normalizar_lado(lado_configurado)
    if configurado != "auto":
        return configurado

    puntuaciones = {
        lado: _confianza_lado(nombre, esqueleto, lado, confianza)
        for lado in ("right", "left")
    }
    preferido = _normalizar_lado(lado_preferido) if lado_preferido else None
    if preferido in {"right", "left"} and puntuaciones[preferido] >= CONFIANZA_MINIMA_ARTICULACION:
        if nombre == "rotacion_muneca":
            return preferido
        otro = "left" if preferido == "right" else "right"
        if puntuaciones[otro] < puntuaciones[preferido] + 0.15:
            return preferido
    if puntuaciones["left"] > puntuaciones["right"]:
        return "left"
    return "right"


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
    confianza: Mapping[str, float] | None = None,
    lado_preferido: str | None = None,
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
    lado_configurado = _normalizar_lado(str(configuracion.get("lado", "auto")))
    lado = resolver_lado_ejercicio(
        nombre,
        esqueleto,
        lado_configurado,
        confianza,
        lado_preferido,
    )

    if not _articulaciones_disponibles(nombre, esqueleto, lado, confianza):
        return RehabAnalysisResult(
            ejercicio=nombre,
            estado=ESTADO_POSTURA_INCOMPLETA,
            color=COLOR_ROJO,
            angulo_actual=None,
            angulo_minimo=minimo,
            angulo_maximo=maximo,
            dentro_rango=False,
            mensajes=[_mensaje_visibilidad(nombre, lado, automatico=lado_configurado == "auto")],
            lado_evaluado=None if lado_configurado == "auto" else lado,
        )

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
            mensajes=[_mensaje_visibilidad(nombre, lado)],
            lado_evaluado=lado,
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
        lado_evaluado=lado,
    )
