"""Sesión acumulada para ejercicios de rehabilitación."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from statistics import median
import time
from typing import Any, Mapping
from uuid import uuid4

from puce_mocap.rehab_analyzer import RehabAnalysisResult
from puce_mocap.rehab_profiles import crear_perfil_demo, movimiento_desde_config
from puce_mocap.movement import AngleRange, MovementDefinition, MovementPhase, RepetitionTracker


@dataclass
class RehabSession:
    """Acumula frames válidos, rango alcanzado y repeticiones estimadas."""

    ejercicio_actual: str
    codigo_paciente: str
    configuracion: Mapping[str, Any] | None = field(default=None, repr=False)
    session_id: str = field(default_factory=lambda: uuid4().hex)
    fuente_datos: str = "mediapipe_live"
    fecha: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    total_frames: int = 0
    frames_validos: int = 0
    frames_dentro_rango: int = 0
    angulo_maximo_alcanzado: float | None = None
    repeticiones_estimadas: int = 0
    fase_actual: str = MovementPhase.CALIBRANDO_INICIO.value
    angulo_referencia_inicio: float | None = None
    rango_inicio_calibrado: AngleRange | None = field(default=None, repr=False)
    estado_calibracion: str = "esperando"
    mensajes_principales: list[str] = field(default_factory=list)
    _inicio_monotonic: float = field(default_factory=time.monotonic, init=False, repr=False)
    _tracker: RepetitionTracker = field(init=False, repr=False)
    _angulo_minimo: float | None = field(default=None, init=False, repr=False)
    _angulo_maximo: float | None = field(default=None, init=False, repr=False)
    _definition_base: MovementDefinition = field(init=False, repr=False)
    _muestras_calibracion: list[tuple[float, float]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        configuracion = self.configuracion
        if configuracion is None:
            configuracion = crear_perfil_demo()["ejercicios"][self.ejercicio_actual]
        self.configuracion = configuracion
        self._definition_base = movimiento_desde_config(configuracion)
        self._tracker = RepetitionTracker(self._definition_base)

    def registrar_resultado(
        self, resultado: RehabAnalysisResult, timestamp: float | None = None
    ) -> RehabAnalysisResult:
        """Registra un frame; las posturas incompletas no cuentan como válidas."""
        if resultado.ejercicio != self.ejercicio_actual:
            raise ValueError(f"El resultado corresponde a {resultado.ejercicio}, no a {self.ejercicio_actual}.")

        self.total_frames += 1
        self._registrar_mensajes(resultado)
        actual_timestamp = time.monotonic() if timestamp is None else float(timestamp)
        if not resultado.frame_valido or resultado.angulo_actual is None:
            self._muestras_calibracion.clear()
            if self.angulo_referencia_inicio is None:
                self.estado_calibracion = "sin_deteccion"
                self.fase_actual = MovementPhase.CALIBRANDO_INICIO.value
                return replace(resultado, fase=MovementPhase.NO_DETECTADO.value)
            actualizacion = self._tracker.update(
                None, actual_timestamp, valid=False
            )
            self.fase_actual = actualizacion.state.value
            return replace(resultado, fase=actualizacion.phase.value)

        self.frames_validos += 1
        self._angulo_minimo = resultado.angulo_minimo
        self._angulo_maximo = resultado.angulo_maximo
        if resultado.dentro_rango:
            self.frames_dentro_rango += 1

        if self.angulo_maximo_alcanzado is None or resultado.angulo_actual > self.angulo_maximo_alcanzado:
            self.angulo_maximo_alcanzado = float(resultado.angulo_actual)

        if self.angulo_referencia_inicio is None and bool(
            self.configuracion.get("calibracion_inicio_automatica", True)
        ):
            calibrado = self._actualizar_calibracion(
                float(resultado.angulo_actual),
                actual_timestamp,
                resultado.forma_correcta,
            )
            if not calibrado:
                self.fase_actual = MovementPhase.CALIBRANDO_INICIO.value
                return replace(resultado, fase=MovementPhase.CALIBRANDO_INICIO.value)
            self.repeticiones_estimadas = self._tracker.repetitions
            self.fase_actual = self._tracker.state.value
            return replace(resultado, fase=MovementPhase.INICIO.value)

        actualizacion = self._tracker.update(
            resultado.angulo_actual,
            actual_timestamp,
            valid=True,
            form_ok=resultado.forma_correcta,
        )
        self.repeticiones_estimadas = actualizacion.repetitions
        self.fase_actual = actualizacion.state.value
        return replace(
            resultado,
            fase=actualizacion.phase.value,
            repeticion_completada=actualizacion.repetition_completed,
        )

    def _actualizar_calibracion(self, angulo: float, timestamp: float, forma_correcta: bool | None) -> bool:
        objetivo = self._definition_base.target_range
        if forma_correcta is False:
            self._muestras_calibracion.clear()
            self.estado_calibracion = "forma_incorrecta"
            return False
        if objetivo.contiene(angulo):
            self._muestras_calibracion.clear()
            self.estado_calibracion = "en_objetivo"
            return False

        duracion = float(self.configuracion.get("calibracion_inicio_ms", 200)) / 1000.0
        estabilidad = float(self.configuracion.get("estabilidad_inicio_grados", 10.0))
        self._muestras_calibracion.append((timestamp, angulo))
        if len(self._muestras_calibracion) < 3:
            self.estado_calibracion = "mantener"
            return False
        first_timestamp = self._muestras_calibracion[0][0]
        valores = [sample_angle for _sample_time, sample_angle in self._muestras_calibracion]
        if timestamp - first_timestamp + 1e-9 < duracion:
            self.estado_calibracion = "mantener"
            return False
        if max(valores) - min(valores) > estabilidad:
            self._muestras_calibracion = [(timestamp, angulo)]
            self.estado_calibracion = "inestable"
            return False

        referencia = float(median(valores))
        dynamic_definition = self._definition_calibrada(referencia)
        self.angulo_referencia_inicio = referencia
        self.rango_inicio_calibrado = dynamic_definition.start_range
        self._tracker = RepetitionTracker(dynamic_definition)
        self._tracker.arm_from_start(referencia, timestamp)
        self._muestras_calibracion.clear()
        self.estado_calibracion = "calibrada"
        return True

    def _definition_calibrada(self, referencia: float) -> MovementDefinition:
        objetivo_original = self._definition_base.target_range
        excursion = float(self.configuracion.get("excursion_minima_grados", 5.0))
        separacion = float(self.configuracion.get("separacion_fases_grados", 2.0))
        tolerancia_maxima = float(self.configuracion.get("tolerancia_retorno_grados", 12.0))

        if referencia < objetivo_original.minimo:
            objetivo = AngleRange(max(objetivo_original.minimo, referencia + excursion), objetivo_original.maximo)
            tolerancia_disponible = objetivo.minimo - referencia - separacion
        else:
            objetivo = AngleRange(objetivo_original.minimo, min(objetivo_original.maximo, referencia - excursion))
            tolerancia_disponible = referencia - objetivo.maximo - separacion
        tolerancia = max(1.0, min(tolerancia_maxima, tolerancia_disponible))
        inicio = AngleRange(referencia - tolerancia, referencia + tolerancia)
        return MovementDefinition(
            start_range=inicio,
            target_range=objetivo,
            hysteresis_deg=self._definition_base.hysteresis_deg,
            dwell_seconds=self._definition_base.dwell_seconds,
            min_cycle_seconds=self._definition_base.min_cycle_seconds,
            invalid_reset_seconds=self._definition_base.invalid_reset_seconds,
            ema_alpha=self._definition_base.ema_alpha,
        )

    def _registrar_mensajes(self, resultado: RehabAnalysisResult) -> None:
        for mensaje in resultado.mensajes:
            if mensaje not in self.mensajes_principales:
                self.mensajes_principales.append(mensaje)

    @property
    def porcentaje_dentro_rango(self) -> float:
        if self.frames_validos == 0:
            return 0.0
        return (self.frames_dentro_rango / self.frames_validos) * 100.0

    @property
    def duracion_segundos(self) -> float:
        return max(0.0, time.monotonic() - self._inicio_monotonic)

    def reiniciar(self) -> None:
        """Reinicia las métricas conservando paciente y ejercicio."""
        self.fecha = datetime.now().isoformat(timespec="seconds")
        self.total_frames = 0
        self.frames_validos = 0
        self.frames_dentro_rango = 0
        self.angulo_maximo_alcanzado = None
        self.repeticiones_estimadas = 0
        self.fase_actual = MovementPhase.CALIBRANDO_INICIO.value
        self.angulo_referencia_inicio = None
        self.rango_inicio_calibrado = None
        self.estado_calibracion = "esperando"
        self.mensajes_principales.clear()
        self._inicio_monotonic = time.monotonic()
        self._tracker = RepetitionTracker(self._definition_base)
        self._muestras_calibracion.clear()
        self._angulo_minimo = None
        self._angulo_maximo = None

    def exportar_resumen(self) -> dict:
        """Exporta la sesión a un diccionario apto para CSV."""
        assert self.configuracion is not None
        inicio = self.rango_inicio_calibrado
        if inicio is None:
            inicio_configurado = self.configuracion["rango_inicio"]
            inicio = AngleRange(float(inicio_configurado["minimo"]), float(inicio_configurado["maximo"]))
        objetivo = self.configuracion["rango_objetivo"]
        return {
            "session_id": self.session_id,
            "fuente_datos": self.fuente_datos,
            "fecha": self.fecha,
            "codigo_paciente": self.codigo_paciente,
            "ejercicio": self.ejercicio_actual,
            "total_frames": self.total_frames,
            "frames_validos": self.frames_validos,
            "frames_dentro_rango": self.frames_dentro_rango,
            "porcentaje_dentro_rango": round(self.porcentaje_dentro_rango, 2),
            "angulo_minimo_inicio": inicio.minimo,
            "angulo_maximo_inicio": inicio.maximo,
            "angulo_referencia_inicio": self.angulo_referencia_inicio,
            "angulo_minimo_objetivo": objetivo["minimo"],
            "angulo_maximo_objetivo": objetivo["maximo"],
            "lado": self.configuracion.get("lado", "auto"),
            "repeticiones_objetivo": self.configuracion["repeticiones_objetivo"],
            "angulo_maximo_alcanzado": (
                None if self.angulo_maximo_alcanzado is None else round(self.angulo_maximo_alcanzado, 2)
            ),
            "repeticiones_estimadas": self.repeticiones_estimadas,
            "duracion_segundos": round(self.duracion_segundos, 2),
            "observaciones": list(self.mensajes_principales),
        }
