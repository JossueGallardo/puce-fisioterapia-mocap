from __future__ import annotations

from pathlib import Path
import sys

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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


EJERCICIOS = {
    "1": ("Sentadilla", evaluar_sentadilla),
    "2": ("Press de hombro", evaluar_press_hombro),
    "3": ("Peso muerto", evaluar_peso_muerto),
}

LANDMARKS_REQUERIDOS = {
    "Sentadilla": ["right_shoulder", "right_hip", "right_knee", "right_ankle"],
    "Press de hombro": ["right_shoulder", "right_elbow", "right_wrist"],
    "Peso muerto": ["right_shoulder", "right_hip", "right_knee", "right_ankle"],
}

ANGULO_PRINCIPAL = {
    "Sentadilla": "angulo_rodilla",
    "Press de hombro": "angulo_codo",
    "Peso muerto": "desviacion_tronco",
}


def _punto_landmark(landmarks, landmark_id: int, min_visibility: float = 0.45):
    landmark = landmarks[landmark_id]
    if getattr(landmark, "visibility", 1.0) < min_visibility:
        return None
    return [float(landmark.x), float(-landmark.y), float(-landmark.z)]


def mediapipe_a_esqueleto_3d(pose_landmarks) -> dict[str, list[float]]:
    """Convierte landmarks de MediaPipe Pose al formato usado por exercise_rules."""
    mp_pose = mp.solutions.pose
    landmarks = pose_landmarks.landmark
    mapa = {
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


def _postura_completa(esqueleto: dict[str, list[float]], ejercicio: str) -> bool:
    return all(nombre in esqueleto for nombre in LANDMARKS_REQUERIDOS[ejercicio])


def _feedback_incompleto(ejercicio: str) -> ExerciseFeedback:
    return ExerciseFeedback(
        ejercicio=ejercicio,
        estado=ESTADO_CORREGIR,
        color=COLOR_ROJO,
        angulos={},
        mensajes=["No se detecta postura completa"],
    )


def _evaluar(ejercicio: str, evaluador, esqueleto: dict[str, list[float]]) -> ExerciseFeedback:
    if not _postura_completa(esqueleto, ejercicio):
        return _feedback_incompleto(ejercicio)
    try:
        if ejercicio == "Press de hombro":
            return evaluador(esqueleto, lado="right")
        return evaluador(esqueleto)
    except ValueError:
        return _feedback_incompleto(ejercicio)


def _texto_limitado(texto: str, max_chars: int = 80) -> str:
    if len(texto) <= max_chars:
        return texto
    return texto[: max_chars - 3] + "..."


def _dibujar_panel(frame, ejercicio: str, feedback: ExerciseFeedback, sesion: ExerciseSession):
    estado_correcto = feedback.es_correcto
    color = (0, 180, 0) if estado_correcto else (0, 0, 220)
    color_nombre = "VERDE" if estado_correcto else "ROJO"
    mensaje = feedback.mensajes[0] if feedback.mensajes else ""
    nombre_angulo = ANGULO_PRINCIPAL[ejercicio]
    valor_angulo = feedback.angulos.get(nombre_angulo)
    texto_angulo = "Angulo principal: N/D" if valor_angulo is None else f"{nombre_angulo}: {valor_angulo:.1f}"

    cv2.rectangle(frame, (0, 0), (frame.shape[1], 190), (20, 20, 20), -1)
    cv2.putText(frame, "PUCE MoCap - Modulo de Pesas", (24, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
    cv2.putText(frame, "Basado en FreeMoCap | MediaPipe Pose como complemento en vivo", (24, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (210, 210, 210), 1)
    cv2.putText(frame, f"Ejercicio: {ejercicio}", (24, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(frame, texto_angulo, (24, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (230, 230, 230), 2)
    cv2.putText(frame, f"{color_nombre} / {feedback.estado}", (24, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.putText(frame, _texto_limitado(mensaje), (24, 178), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (235, 235, 235), 1)

    metricas = f"Reps: {sesion.repeticiones} | Correcto: {sesion.porcentaje_correcto:.1f}% | Frames: {sesion.total_frames}"
    cv2.putText(frame, metricas, (24, frame.shape[0] - 48), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
    cv2.putText(frame, "1 Sentadilla | 2 Press hombro | 3 Peso muerto | r Reiniciar | q Salir", (24, frame.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 220), 1)


def main():
    if mp is None:
        print("MediaPipe no esta instalado. Ejecuta: python -m pip install mediapipe")
        return

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No se pudo abrir la camara 0. Verifica permisos de camara en Windows.")
        return

    ejercicio, evaluador = EJERCICIOS["1"]
    sesion = ExerciseSession(ejercicio)
    reporte_path = REPO_ROOT / "reports" / "semana_3_live_pose_report.csv"

    print("Demo live iniciado. Teclas: 1 sentadilla, 2 press, 3 peso muerto, r reiniciar, q salir.")

    with mp_pose.Pose(model_complexity=1, min_detection_confidence=0.6, min_tracking_confidence=0.6) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("No se pudo leer un frame de la camara.")
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultado = pose.process(rgb)

            if resultado.pose_landmarks:
                mp_drawing.draw_landmarks(frame, resultado.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                esqueleto = mediapipe_a_esqueleto_3d(resultado.pose_landmarks)
                feedback = _evaluar(ejercicio, evaluador, esqueleto)
            else:
                feedback = _feedback_incompleto(ejercicio)

            sesion.registrar_feedback(feedback)
            _dibujar_panel(frame, ejercicio, feedback, sesion)
            cv2.imshow("PUCE MoCap - Semana 3 Live Pose", frame)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                break
            if tecla in (ord("1"), ord("2"), ord("3")):
                ejercicio, evaluador = EJERCICIOS[chr(tecla)]
                sesion = ExerciseSession(ejercicio)
            elif tecla == ord("r"):
                sesion = ExerciseSession(ejercicio)

    cap.release()
    cv2.destroyAllWindows()
    generar_reporte_csv(sesion.exportar_resumen(), reporte_path)
    print(f"Reporte CSV generado: {reporte_path}")


if __name__ == "__main__":
    main()

