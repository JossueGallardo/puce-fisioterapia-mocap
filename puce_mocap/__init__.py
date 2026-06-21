"""Herramientas PUCE para analisis de movimiento sobre FreeMoCap."""

from puce_mocap.angle_utils import calcular_angulo, calcular_angulo_vectores
from puce_mocap.exercise_rules import (
    ExerciseFeedback,
    evaluar_peso_muerto,
    evaluar_press_hombro,
    evaluar_sentadilla,
)
from puce_mocap.exercise_session import ExerciseSession
from puce_mocap.freemocap_adapter import (
    evaluar_ejercicio_freemocap,
    normalizar_articulaciones_freemocap,
    normalizar_esqueleto_marcha_freemocap,
)
from puce_mocap.gait_analyzer import GaitAnalysisResult, analizar_marcha
from puce_mocap.gait_session import GaitSession
from puce_mocap.movement import AngleRange, MovementDefinition, MovementPhase, RepetitionTracker
from puce_mocap.freemocap_session import FreeMoCapSessionProvider
from puce_mocap.rehab_analyzer import RehabAnalysisResult, WristRotationCalibrator, evaluar_ejercicio_rehabilitacion
from puce_mocap.rehab_profiles import (
    cargar_perfil_paciente,
    crear_perfil_demo,
    normalizar_perfil_paciente,
    validar_perfil_paciente,
)
from puce_mocap.rehab_session import RehabSession
from puce_mocap.skeleton_frame import PoseFrameProvider, SkeletonFrame

__all__ = [
    "ExerciseFeedback",
    "ExerciseSession",
    "AngleRange",
    "MovementDefinition",
    "MovementPhase",
    "RepetitionTracker",
    "SkeletonFrame",
    "PoseFrameProvider",
    "FreeMoCapSessionProvider",
    "GaitAnalysisResult",
    "GaitSession",
    "RehabAnalysisResult",
    "RehabSession",
    "WristRotationCalibrator",
    "analizar_marcha",
    "calcular_angulo",
    "calcular_angulo_vectores",
    "evaluar_peso_muerto",
    "evaluar_press_hombro",
    "evaluar_sentadilla",
    "evaluar_ejercicio_rehabilitacion",
    "cargar_perfil_paciente",
    "crear_perfil_demo",
    "validar_perfil_paciente",
    "normalizar_perfil_paciente",
    "evaluar_ejercicio_freemocap",
    "normalizar_articulaciones_freemocap",
    "normalizar_esqueleto_marcha_freemocap",
]
