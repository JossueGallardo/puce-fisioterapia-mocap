"""Estado y acciones de la interfaz web."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
import threading
import time
from typing import Any, Mapping
from uuid import uuid4

from puce_mocap.exercise_rules import (
    ESTADO_POSTURA_INCOMPLETA,
    ExerciseFeedback,
    evaluar_peso_muerto,
    evaluar_press_hombro,
    evaluar_sentadilla,
)
from puce_mocap.exercise_session import DEFINICIONES_MOVIMIENTO, ExerciseSession
from puce_mocap.freemocap_session import MEDIAPIPE_BODY_LANDMARKS, FreeMoCapSessionProvider
from puce_mocap.gait_analyzer import analizar_marcha
from puce_mocap.gait_session import GaitSession
from puce_mocap.gait_temporal import GaitCycleAnalyzer
from puce_mocap.movement import AngleRange, MovementDefinition
from puce_mocap.rehab_analyzer import (
    ORIENTACION_RECOMENDADA,
    WristRotationCalibrator,
    evaluar_ejercicio_rehabilitacion,
    resolver_lado_ejercicio,
)
from puce_mocap.rehab_profiles import (
    EJERCICIOS_REHABILITACION,
    crear_perfil_demo,
    normalizar_perfil_paciente,
)
from puce_mocap.rehab_session import RehabSession
from puce_mocap.reports_v2 import INSTITUTIONAL, export_gait_session, export_rehab_sessions, export_weight_sessions
from puce_mocap.skeleton_frame import SkeletonFrame
from puce_mocap.web.camera_service import BrowserPoseProcessor


DISCLAIMER = "Herramienta de apoyo; no sustituye la evaluación de un fisioterapeuta."
WEIGHT_EXERCISES = ("Sentadilla", "Press de hombro", "Peso muerto")
MODULES = {
    "weights": "Módulo 1 - Ejercicios con pesas",
    "rehab": "Módulo 2 - Rehabilitación",
    "gait": "Módulo 3 - Análisis de marcha",
}
REHAB_LABELS = {
    "flexion_codo": "Flexión de codo",
    "abduccion_hombro": "Abducción de hombro",
    "rotacion_muneca": "Rotación de muñeca",
    "extension_rodilla": "Extensión de rodilla",
    "dorsiflexion_tobillo": "Dorsiflexión de tobillo",
    "elevacion_pierna_recta": "Elevación de pierna recta",
}
PHASE_LABELS = {
    "calibrando_inicio": "Calibrando inicio",
    "esperando_inicio": "Esperando postura inicial",
    "buscando_objetivo": "Buscando objetivo",
    "regresando_inicio": "Regresando al inicio",
    "inicio": "Inicio",
    "objetivo": "Objetivo",
    "transicion": "Transición",
}


class WebActionError(ValueError):
    """Error esperado de una acción solicitada por la interfaz web."""


def _phase_text(phase: str) -> str:
    return PHASE_LABELS.get(phase, phase.replace("_", " ").capitalize())


def _as_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WebActionError(f"{field_name} debe ser numérico.") from exc


def _as_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise WebActionError(f"{field_name} debe ser entero.") from exc


def _range_payload(payload: Mapping[str, Any], key: str) -> dict[str, float]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise WebActionError(f"Falta el rango {key}.")
    return {
        "minimo": _as_float(value.get("minimo"), f"{key}.minimo"),
        "maximo": _as_float(value.get("maximo"), f"{key}.maximo"),
    }


class PuceWebController:
    """Controlador de una sesión web de un solo usuario."""

    def __init__(self, pose_processor: BrowserPoseProcessor | None = None) -> None:
        self._lock = threading.RLock()
        self.pose_processor = pose_processor or BrowserPoseProcessor()
        self._uploads = tempfile.TemporaryDirectory(prefix="puce-mocap-web-")
        self.module = "weights"
        self.source_mode = "none"
        self.status = "Sistema listo. Active la cámara o cargue una sesión procesada."
        self.last_report_path: str | None = None
        self.metrics: list[dict[str, str]] = []
        self.browser_camera_active = False
        self.browser_camera_label = ""
        self.browser_camera_resolution = {"width": 0, "height": 0}
        self.visualization: dict[str, Any] | None = None
        self.provider: FreeMoCapSessionProvider | None = None
        self.provider_frame_index = 0

        self.weight_session_id = uuid4().hex
        self.weight_definitions = {name: definition for name, (_angle, definition) in DEFINICIONES_MOVIMIENTO.items()}
        self.weight_sessions: dict[str, ExerciseSession] = {}
        self.weight_exercise = "Sentadilla"
        self.weight_recording = False
        self.weight_dirty = False
        self.weight_patient = {
            "codigo_paciente": "PAC-001",
            "nombre_paciente": "Paciente de prueba",
            "lesion": "Seguimiento general ficticio",
            "observaciones_paciente": "Sin datos reales",
        }
        self._reset_weight_sessions()

        self.rehab_profile = crear_perfil_demo()
        self.rehab_session_id = uuid4().hex
        self.rehab_sessions: dict[str, RehabSession] = {}
        self.rehab_exercise = next(iter(self.rehab_profile["ejercicios"]))
        self.rehab_recording = False
        self.rehab_dirty = False
        self.rehab_calibrator = WristRotationCalibrator()
        self.latest_points: Mapping[str, Any] = {}
        self.latest_confidence: Mapping[str, float] = {}
        self.rehab_evaluated_side: str | None = None
        self._rebuild_rehab_sessions()

        self.gait_session = GaitSession()
        self.gait_temporal = GaitCycleAnalyzer()
        self.gait_recording = False
        self.gait_exported = False
        self.gait_view = "Lateral"
        self._set_default_metrics()

    def close(self) -> None:
        self.pose_processor.close()
        if self.provider is not None:
            self.provider.close()
            self.provider = None
        self._uploads.cleanup()

    def app_info(self) -> dict[str, Any]:
        return {
            "institutional": dict(INSTITUTIONAL),
            "disclaimer": DISCLAIMER,
            "modules": [{"key": key, "label": label} for key, label in MODULES.items()],
            "weight_exercises": list(WEIGHT_EXERCISES),
            "rehab_exercises": [
                {
                    "key": key,
                    "label": REHAB_LABELS[key],
                    "orientation": ORIENTACION_RECOMENDADA[key],
                }
                for key in EJERCICIOS_REHABILITACION
            ],
            "local_only": False,
            "deployment": {
                "browser_camera": True,
                "requires_https_outside_localhost": True,
                "server_filesystem_paths": False,
            },
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            provider = None
            if self.provider is not None:
                provider = {
                    "frame_count": self.provider.frame_count,
                    "frame_index": self.provider_frame_index,
                    "length_unit": self.provider.length_unit,
                    "filename": self.provider.data_path.name,
                }
            report = None
            if self.last_report_path:
                path = Path(self.last_report_path)
                report = {"available": path.is_file(), "filename": path.name}
            return {
                "module": self.module,
                "module_label": MODULES[self.module],
                "source": {
                    "mode": self.source_mode,
                    "camera_active": self.browser_camera_active,
                    "camera_status": "Cámara del navegador activa." if self.browser_camera_active else "Cámara inactiva.",
                    "camera": {
                        "label": self.browser_camera_label,
                        **self.browser_camera_resolution,
                    },
                    "freemocap": provider,
                },
                "status": self.status,
                "disclaimer": DISCLAIMER,
                "metrics": list(self.metrics),
                "last_report": report,
                "visualization": deepcopy(self.visualization),
                "weights": self._weights_state(),
                "rehab": self._rehab_state(),
                "gait": self._gait_state(),
            }

    def set_module(self, module: str) -> None:
        with self._lock:
            if module not in MODULES:
                raise WebActionError("Módulo no válido.")
            self.module = module
            self._set_default_metrics()
            self.status = "Módulo seleccionado. " + DISCLAIMER
            self._process_current_provider_frame_locked()

    def start_camera(self, payload: Mapping[str, Any]) -> None:
        with self._lock:
            width = _as_int(payload.get("width", 640), "width")
            height = _as_int(payload.get("height", 480), "height")
            label = str(payload.get("device_label", "")).strip()
            self.source_mode = "browser_camera"
            if self.provider is not None:
                self.provider.close()
            self.provider = None
            self.visualization = None
            self.browser_camera_active = True
            self.browser_camera_label = label
            self.browser_camera_resolution = {"width": width, "height": height}
            self.status = "Cámara activa. El video permanece en el navegador y el análisis se procesa en el servidor."

    def stop_camera(self) -> None:
        with self._lock:
            self.browser_camera_active = False
            self.visualization = None
            if self.source_mode == "browser_camera":
                self.source_mode = "none"
            self.status = "Cámara detenida. " + DISCLAIMER

    def process_browser_frame(self, image_bytes: bytes) -> dict[str, Any]:
        with self._lock:
            if not self.browser_camera_active:
                raise WebActionError("Active la cámara antes de enviar fotogramas.")
        try:
            result = self.pose_processor.process_jpeg(image_bytes)
        except ValueError as exc:
            raise WebActionError(str(exc)) from exc
        with self._lock:
            self._process_skeleton_locked(result.skeleton)
            self.visualization = {
                "kind": "image_landmarks",
                "landmarks": result.landmarks,
                "detected": bool(result.landmarks),
                "processing_ms": round(result.processing_ms, 1),
            }
            return deepcopy(self.visualization)

    def allocate_freemocap_upload(self, filename: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(filename).name)
        if not safe_name.endswith("_body_3d_xyz.npy"):
            raise WebActionError("Seleccione el archivo *_body_3d_xyz.npy generado por FreeMoCap.")
        output = Path(self._uploads.name) / uuid4().hex / "output_data"
        output.mkdir(parents=True)
        return output / safe_name

    def load_freemocap_upload(self, uploaded_path: Path, unit: str = "sin_especificar") -> None:
        with self._lock:
            if self.provider is not None:
                self.provider.close()
            self.provider = FreeMoCapSessionProvider(uploaded_path.parent.parent, unit)
            self.provider_frame_index = 0
            self.source_mode = "freemocap"
            self.browser_camera_active = False
            self.status = (
                f"Sesión FreeMoCap cargada: {self.provider.frame_count} fotogramas; "
                f"unidad {self.provider.length_unit}."
            )
            self._process_current_provider_frame_locked()

    def process_freemocap_frame(self, payload: Mapping[str, Any]) -> None:
        with self._lock:
            if self.provider is None:
                raise WebActionError("No hay una sesión FreeMoCap cargada.")
            index = _as_int(payload.get("index", self.provider_frame_index), "index")
            if not 0 <= index < self.provider.frame_count:
                raise WebActionError("Fotograma fuera de rango.")
            self.provider_frame_index = index
            self.source_mode = "freemocap"
            self._process_current_provider_frame_locked()

    def configure_weights(self, payload: Mapping[str, Any]) -> None:
        with self._lock:
            exercise = payload.get("exercise")
            if isinstance(exercise, str) and exercise:
                if exercise not in WEIGHT_EXERCISES:
                    raise WebActionError("Ejercicio de pesas no válido.")
                self.weight_exercise = exercise
            patient = payload.get("patient")
            if isinstance(patient, Mapping):
                for key in self.weight_patient:
                    if key in patient:
                        self.weight_patient[key] = str(patient[key]).strip()
            ranges = payload.get("ranges")
            if isinstance(ranges, Mapping):
                definition = MovementDefinition(
                    start_range=AngleRange(
                        _as_float(ranges.get("start_min"), "start_min"),
                        _as_float(ranges.get("start_max"), "start_max"),
                    ),
                    target_range=AngleRange(
                        _as_float(ranges.get("target_min"), "target_min"),
                        _as_float(ranges.get("target_max"), "target_max"),
                    ),
                )
                if definition != self.weight_definitions[self.weight_exercise]:
                    self.weight_definitions[self.weight_exercise] = definition
                    self.weight_sessions[self.weight_exercise].configurar_movimiento(definition)
                    self.weight_recording = False
            self.status = "Configuración de pesas aplicada."

    def start_weights(self, payload: Mapping[str, Any] | None = None) -> None:
        with self._lock:
            if payload:
                self.configure_weights(payload)
            required = ("codigo_paciente", "nombre_paciente", "lesion")
            if not all(self.weight_patient[key] for key in required):
                raise WebActionError("Complete nombre, código y condición del paciente antes de iniciar.")
            self.weight_recording = True
            self.status = "Ejercicio iniciado. Complete inicio -> objetivo -> inicio."

    def pause_weights(self) -> None:
        with self._lock:
            self.weight_recording = False
            self.status = "Ejercicio en pausa. No se contabilizarán repeticiones."

    def reset_weights(self) -> None:
        with self._lock:
            self.weight_sessions[self.weight_exercise].reiniciar()
            self.weight_recording = False
            self.status = "Ejercicio reiniciado. Pulse iniciar cuando el paciente esté preparado."
            self._set_default_metrics()

    def save_weights(self) -> None:
        with self._lock:
            if not self.weight_dirty:
                self.status = "No hay datos nuevos de pesas para guardar."
                return
            path = export_weight_sessions(
                ({**session.exportar_resumen(), **self.weight_patient} for session in self.weight_sessions.values())
            )
            self.last_report_path = str(path)
            self.weight_dirty = False
            self.weight_recording = False
            self.weight_session_id = uuid4().hex
            self._reset_weight_sessions()
            self.status = f"Reporte guardado en {path}."

    def configure_rehab(self, payload: Mapping[str, Any]) -> None:
        with self._lock:
            exercise = payload.get("exercise")
            if isinstance(exercise, str) and exercise:
                if exercise not in EJERCICIOS_REHABILITACION:
                    raise WebActionError("Ejercicio de rehabilitación no válido.")
                if exercise != self.rehab_exercise:
                    self.rehab_evaluated_side = None
                self.rehab_exercise = exercise
            if self.rehab_recording:
                raise WebActionError("Pause el ejercicio antes de cambiar el perfil o los rangos.")

            profile = deepcopy(self.rehab_profile)
            patient = payload.get("patient")
            if isinstance(patient, Mapping):
                field_map = {
                    "nombre": "nombre",
                    "codigo_paciente": "codigo_paciente",
                    "lesion": "lesion",
                    "observaciones": "observaciones",
                }
                for source, target in field_map.items():
                    if source in patient:
                        profile[target] = str(patient[source]).strip()
            config_payload = payload.get("config")
            if isinstance(config_payload, Mapping):
                config = dict(profile["ejercicios"][self.rehab_exercise])
                config["rango_inicio"] = _range_payload(config_payload, "rango_inicio")
                config["rango_objetivo"] = _range_payload(config_payload, "rango_objetivo")
                config["repeticiones_objetivo"] = _as_int(
                    config_payload.get("repeticiones_objetivo"), "repeticiones_objetivo"
                )
                config["lado"] = str(config_payload.get("lado", config.get("lado", "auto")))
                profile["ejercicios"][self.rehab_exercise] = config
            normalized = normalizar_perfil_paciente(profile)
            if normalized != self.rehab_profile:
                if self.rehab_dirty:
                    raise WebActionError("Guarde el reporte antes de cambiar datos de una sesión en curso.")
                self.rehab_profile = normalized
                self._rebuild_rehab_sessions()
                self.rehab_calibrator = WristRotationCalibrator()
                self.rehab_evaluated_side = None
            self.status = "Perfil y rangos aplicados correctamente."

    def start_rehab(self, payload: Mapping[str, Any] | None = None) -> None:
        with self._lock:
            if payload:
                self.configure_rehab(payload)
            if self.rehab_exercise == "rotacion_muneca" and not self.rehab_calibrator.calibrado:
                raise WebActionError("Calibre primero la posición neutral de la muñeca.")
            self.rehab_recording = True
            session = self.rehab_sessions[self.rehab_exercise]
            if session.angulo_referencia_inicio is None:
                self.status = "Mantenga una postura inicial cómoda y estable durante un momento."
            else:
                self.status = f"Continuando con referencia inicial de {session.angulo_referencia_inicio:.1f}°."

    def pause_rehab(self) -> None:
        with self._lock:
            self.rehab_recording = False
            self.status = "Ejercicio en pausa. No se contabilizarán repeticiones."

    def reset_rehab(self) -> None:
        with self._lock:
            self.rehab_sessions[self.rehab_exercise].reiniciar()
            self.rehab_evaluated_side = None
            self.rehab_recording = False
            self.status = "Ejercicio reiniciado."
            self._set_default_metrics()

    def calibrate_wrist(self) -> None:
        with self._lock:
            try:
                configured = self.rehab_profile["ejercicios"]["rotacion_muneca"].get("lado", "auto")
                side = resolver_lado_ejercicio(
                    "rotacion_muneca",
                    self.latest_points,
                    configured,
                    self.latest_confidence,
                    self.rehab_evaluated_side,
                )
                self.rehab_calibrator.calibrar(self.latest_points, side)
                self.rehab_evaluated_side = side
            except ValueError as exc:
                raise WebActionError(str(exc)) from exc
            side_text = "derecha" if side == "right" else "izquierda"
            self.status = f"Calibración neutral de muñeca completada en la extremidad {side_text}."

    def load_rehab_profile_json(self, content: bytes) -> None:
        try:
            profile = json.loads(content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebActionError("El archivo seleccionado no contiene un perfil JSON válido.") from exc
        with self._lock:
            self.rehab_profile = normalizar_perfil_paciente(profile)
            self.rehab_exercise = next(iter(self.rehab_profile["ejercicios"]))
            self.rehab_session_id = uuid4().hex
            self.rehab_dirty = False
            self.rehab_recording = False
            self.rehab_calibrator = WristRotationCalibrator()
            self.rehab_evaluated_side = None
            self._rebuild_rehab_sessions()
            self.status = "Perfil cargado desde el dispositivo."

    def rehab_profile_json(self) -> bytes:
        with self._lock:
            normalized = normalizar_perfil_paciente(self.rehab_profile)
            return (json.dumps(normalized, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    def latest_report(self) -> Path:
        with self._lock:
            if not self.last_report_path:
                raise WebActionError("Todavía no hay un reporte disponible.")
            path = Path(self.last_report_path)
            if not path.is_file():
                raise WebActionError("El último reporte ya no está disponible.")
            return path

    def save_rehab(self) -> None:
        with self._lock:
            if not self.rehab_dirty:
                self.status = "No hay datos nuevos de rehabilitación para guardar."
                return
            path = export_rehab_sessions(
                (session.exportar_resumen() for session in self.rehab_sessions.values()), self.rehab_profile
            )
            self.last_report_path = str(path)
            self.rehab_dirty = False
            self.rehab_recording = False
            self.rehab_session_id = uuid4().hex
            self.rehab_evaluated_side = None
            self._rebuild_rehab_sessions()
            self.status = f"Reporte guardado en {path}."

    def configure_gait(self, payload: Mapping[str, Any]) -> None:
        with self._lock:
            view = str(payload.get("view", self.gait_view) or self.gait_view)
            if view.lower() not in {"lateral", "frontal"}:
                raise WebActionError("Vista de marcha no válida.")
            self.gait_view = "Frontal" if view.lower() == "frontal" else "Lateral"
            self.status = "Configuración de marcha aplicada."

    def start_gait(self) -> None:
        with self._lock:
            if self.gait_exported:
                self._reset_gait_locked()
            self.gait_recording = True
            self.status = "Sesión iniciada."

    def stop_gait(self) -> None:
        with self._lock:
            self.gait_recording = False
            if self.gait_exported or self.gait_session.frames_validos == 0:
                self.status = "Sesión sin datos. " + DISCLAIMER
                return
            path = export_gait_session(self.gait_session.exportar_resumen())
            self.last_report_path = str(path)
            self.gait_exported = True
            self.status = f"Sesión finalizada. Reporte: {path}. {DISCLAIMER}"

    def reset_gait(self) -> None:
        with self._lock:
            self._reset_gait_locked()
            self.status = "Sesión reiniciada."
            self._set_default_metrics()

    def process_skeleton(self, frame: SkeletonFrame) -> None:
        with self._lock:
            self._process_skeleton_locked(frame)

    def _process_current_provider_frame_locked(self) -> None:
        if self.provider is None:
            return
        frame = self.provider.get_frame(self.provider_frame_index)
        self._process_skeleton_locked(frame)
        self.visualization = self._project_skeleton(frame)

    def _process_skeleton_locked(self, frame: SkeletonFrame) -> None:
        if self.module == "weights":
            self._process_weights_locked(frame)
        elif self.module == "rehab":
            self._process_rehab_locked(frame)
        elif self.module == "gait":
            self._process_gait_locked(frame)

    def _process_weights_locked(self, frame: SkeletonFrame) -> None:
        try:
            if self.weight_exercise == "Sentadilla":
                feedback = evaluar_sentadilla(frame.points)
            elif self.weight_exercise == "Press de hombro":
                feedback = evaluar_press_hombro(frame.points)
            else:
                feedback = evaluar_peso_muerto(frame.points, vista="lateral")
        except ValueError:
            feedback = ExerciseFeedback(
                self.weight_exercise,
                ESTADO_POSTURA_INCOMPLETA,
                "rojo",
                mensajes=["No se detecta postura completa."],
                frame_valido=False,
            )

        session = self.weight_sessions[self.weight_exercise]
        session.fuente_datos = frame.source
        if self.weight_recording:
            feedback = session.registrar_feedback(feedback, frame.timestamp)
            self.weight_dirty = True
        angle_name = feedback.angulo_principal
        angle = feedback.angulos.get(angle_name) if angle_name else None
        self.metrics = [
            {"label": "Ángulo", "value": "N/D" if angle is None else f"{angle:.1f}°"},
            {"label": "Fase", "value": _phase_text(feedback.fase) if self.weight_recording else "En espera"},
            {"label": "Repeticiones", "value": str(session.repeticiones)},
            {
                "label": "Postura",
                "value": "Correcta" if feedback.forma_correcta else "N/D" if feedback.forma_correcta is None else "Corregir",
            },
        ]
        if self.weight_recording:
            self.status = feedback.mensajes[0] if feedback.mensajes else DISCLAIMER
        elif feedback.mensajes:
            self.status = "Vista previa: " + feedback.mensajes[0]

    def _process_rehab_locked(self, frame: SkeletonFrame) -> None:
        self.latest_points = frame.points
        self.latest_confidence = frame.confidence
        result = evaluar_ejercicio_rehabilitacion(
            self.rehab_exercise,
            frame.points,
            self.rehab_profile,
            self.rehab_calibrator if self.rehab_exercise == "rotacion_muneca" else None,
            frame.confidence,
            self.rehab_evaluated_side,
        )
        if result.frame_valido and result.lado_evaluado is not None:
            self.rehab_evaluated_side = result.lado_evaluado
        session = self.rehab_sessions[self.rehab_exercise]
        session.fuente_datos = frame.source
        if self.rehab_recording:
            result = session.registrar_resultado(result, frame.timestamp)
            if result.frame_valido:
                self.rehab_dirty = True
        self.metrics = [
            {"label": "Ángulo", "value": "N/D" if result.angulo_actual is None else f"{result.angulo_actual:.1f}°"},
            {"label": "Fase", "value": _phase_text(session.fase_actual) if self.rehab_recording else "En espera"},
            {"label": "Repeticiones", "value": str(session.repeticiones_estimadas)},
            {"label": "En rango", "value": "Sí" if result.dentro_rango else "No"},
        ]
        side_text = "derecha" if result.lado_evaluado == "right" else "izquierda"
        orientation = ORIENTACION_RECOMENDADA[self.rehab_exercise]
        orientation_text = "cámara frontal" if orientation == "frontal" else "cámara lateral u oblicua"
        if self.rehab_recording:
            if not result.frame_valido:
                self.status = result.mensajes[0]
            elif session.angulo_referencia_inicio is None:
                target = self.rehab_profile["ejercicios"][self.rehab_exercise]["rango_objetivo"]
                if session.estado_calibracion == "en_objetivo":
                    self.status = (
                        f"Ángulo actual: {result.angulo_actual:.1f}°. "
                        f"Adopte una postura de reposo fuera del objetivo "
                        f"{target['minimo']:.0f}°–{target['maximo']:.0f}° y manténgala."
                    )
                elif session.estado_calibracion == "forma_incorrecta":
                    self.status = (
                        result.mensajes[-1]
                        if result.mensajes
                        else "Corrija la postura antes de calibrar el inicio."
                    )
                elif session.estado_calibracion == "inestable":
                    self.status = (
                        f"Ángulo actual: {result.angulo_actual:.1f}°. "
                        "Mantenga la postura quieta para calibrar el inicio."
                    )
                else:
                    self.status = (
                        f"Extremidad {side_text}; {orientation_text}. "
                        f"Mantenga esta postura cómoda y estable. Ángulo actual: {result.angulo_actual:.1f}°."
                    )
            elif session.fase_actual == "esperando_inicio":
                start = session.rango_inicio_calibrado
                assert start is not None
                self.status = (
                    f"Inicio calibrado en {session.angulo_referencia_inicio:.1f}°. "
                    f"Regrese a {start.minimo:.0f}°–{start.maximo:.0f}° para rearmar el ciclo."
                )
            elif session.fase_actual == "buscando_objetivo":
                target = self.rehab_profile["ejercicios"][self.rehab_exercise]["rango_objetivo"]
                self.status = (
                    f"Inicio calibrado en {session.angulo_referencia_inicio:.1f}°. "
                    f"Alcance el rango objetivo "
                    f"{target['minimo']:.0f}°–{target['maximo']:.0f}°."
                )
            elif session.fase_actual == "regresando_inicio":
                start = session.rango_inicio_calibrado
                assert start is not None
                self.status = (
                    f"Objetivo alcanzado. Regrese cerca de la referencia "
                    f"{session.angulo_referencia_inicio:.1f}° "
                    f"({start.minimo:.0f}°–{start.maximo:.0f}°) y mantenga la postura."
                )
            else:
                self.status = result.mensajes[0] if result.mensajes else DISCLAIMER
        elif result.mensajes:
            self.status = "Vista previa: " + result.mensajes[0]

    def _process_gait_locked(self, frame: SkeletonFrame) -> None:
        initial = analizar_marcha(frame.points, vista=self.gait_view)
        if not initial.frame_valido:
            result = initial
        else:
            right = float(initial.metricas["angulo_rodilla_derecha"])
            left = float(initial.metricas["angulo_rodilla_izquierda"])
            separation = None
            if "left_ankle" in frame.points and "right_ankle" in frame.points:
                separation = abs(float(frame.points["left_ankle"][0]) - float(frame.points["right_ankle"][0]))
            temporal = self.gait_temporal.update(
                right,
                left,
                separation,
                time.monotonic() if frame.timestamp is None else frame.timestamp,
                view=self.gait_view,
                length_unit=frame.length_unit,
            )
            result = analizar_marcha(frame.points, vista=self.gait_view, metricas_temporales=temporal)
        self.gait_session.fuente_datos = frame.source
        if self.gait_recording:
            self.gait_session.registrar_resultado(result)
        metrics = result.metricas
        length = metrics.get("longitud_paso")
        self.metrics = [
            {
                "label": "Rodilla derecha",
                "value": "N/D" if metrics.get("angulo_rodilla_derecha") is None else f"{metrics['angulo_rodilla_derecha']:.1f}°",
            },
            {
                "label": "Rodilla izquierda",
                "value": "N/D" if metrics.get("angulo_rodilla_izquierda") is None else f"{metrics['angulo_rodilla_izquierda']:.1f}°",
            },
            {
                "label": "Asimetría de ciclos",
                "value": "N/D" if metrics.get("asimetria_rodillas") is None else f"{metrics['asimetria_rodillas']:.1f}°",
            },
            {
                "label": "Longitud de paso",
                "value": "N/D" if length is None else f"{length:.3f} {metrics['unidad_longitud']}",
            },
        ]
        self.status = result.mensajes[0] if result.mensajes else DISCLAIMER

    def _reset_weight_sessions(self) -> None:
        self.weight_sessions = {
            name: ExerciseSession(name, session_id=self.weight_session_id, definicion=self.weight_definitions[name])
            for name in WEIGHT_EXERCISES
        }

    def _rebuild_rehab_sessions(self) -> None:
        self.rehab_sessions = {
            key: RehabSession(key, self.rehab_profile["codigo_paciente"], config, session_id=self.rehab_session_id)
            for key, config in self.rehab_profile["ejercicios"].items()
        }

    def _reset_gait_locked(self) -> None:
        self.gait_session = GaitSession()
        self.gait_temporal.reset()
        self.gait_recording = False
        self.gait_exported = False

    def _set_default_metrics(self) -> None:
        if self.module == "weights":
            self.metrics = [
                {"label": "Ángulo", "value": "N/D"},
                {"label": "Fase", "value": "En espera"},
                {"label": "Repeticiones", "value": "0"},
                {"label": "Postura", "value": "N/D"},
            ]
        elif self.module == "rehab":
            self.metrics = [
                {"label": "Ángulo", "value": "N/D"},
                {"label": "Fase", "value": "En espera"},
                {"label": "Repeticiones", "value": "0"},
                {"label": "En rango", "value": "No"},
            ]
        else:
            self.metrics = [
                {"label": "Rodilla derecha", "value": "N/D"},
                {"label": "Rodilla izquierda", "value": "N/D"},
                {"label": "Asimetría de ciclos", "value": "N/D"},
                {"label": "Longitud de paso", "value": "N/D"},
            ]

    def _weights_state(self) -> dict[str, Any]:
        definitions = {}
        for name, definition in self.weight_definitions.items():
            definitions[name] = {
                "start_min": definition.start_range.minimo,
                "start_max": definition.start_range.maximo,
                "target_min": definition.target_range.minimo,
                "target_max": definition.target_range.maximo,
            }
        return {
            "exercise": self.weight_exercise,
            "recording": self.weight_recording,
            "patient": dict(self.weight_patient),
            "definitions": definitions,
            "repetitions": self.weight_sessions[self.weight_exercise].repeticiones,
        }

    def _rehab_state(self) -> dict[str, Any]:
        return {
            "exercise": self.rehab_exercise,
            "recording": self.rehab_recording,
            "profile": deepcopy(self.rehab_profile),
            "calibrated_wrist": self.rehab_calibrator.calibrado,
            "evaluated_side": self.rehab_evaluated_side,
            "start_reference": self.rehab_sessions[self.rehab_exercise].angulo_referencia_inicio,
            "calibration_status": self.rehab_sessions[self.rehab_exercise].estado_calibracion,
            "repetitions": self.rehab_sessions[self.rehab_exercise].repeticiones_estimadas,
        }

    def _gait_state(self) -> dict[str, Any]:
        return {
            "view": self.gait_view,
            "recording": self.gait_recording,
            "exported": self.gait_exported,
            "frames_validos": self.gait_session.frames_validos,
            "estado_global": self.gait_session.estado_global,
        }

    @staticmethod
    def _project_skeleton(frame: SkeletonFrame) -> dict[str, Any] | None:
        visible = {
            name: point
            for name, point in frame.points.items()
            if len(point) >= 2 and name in MEDIAPIPE_BODY_LANDMARKS
        }
        if not visible:
            return None
        xs = [float(point[0]) for point in visible.values()]
        ys = [float(point[1]) for point in visible.values()]
        span_x = max(max(xs) - min(xs), 1e-6)
        span_y = max(max(ys) - min(ys), 1e-6)
        padding = 0.12
        landmarks = []
        for name in MEDIAPIPE_BODY_LANDMARKS:
            point = visible.get(name)
            if point is None:
                landmarks.append({"x": 0.0, "y": 0.0, "visibility": 0.0})
                continue
            x = padding + (float(point[0]) - min(xs)) / span_x * (1.0 - 2.0 * padding)
            y = padding + (max(ys) - float(point[1])) / span_y * (1.0 - 2.0 * padding)
            landmarks.append({"x": x, "y": y, "visibility": 1.0})
        return {"kind": "projected_skeleton", "landmarks": landmarks, "detected": True}
