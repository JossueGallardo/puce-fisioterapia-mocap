"""Worker Qt para captura e inferencia sin bloquear la interfaz."""

from __future__ import annotations

from dataclasses import dataclass
import sys
import threading
import time

from PySide6.QtCore import QThread, Signal

from puce_mocap.freemocap_session import MEDIAPIPE_BODY_LANDMARKS
from puce_mocap.skeleton_frame import SkeletonFrame


@dataclass(frozen=True)
class LivePoseResult:
    image_rgb: object
    skeleton: SkeletonFrame


class CameraPoseWorker(QThread):
    status_changed = Signal(str)
    model_ready = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = threading.Event()
        self._lock = threading.Lock()
        self._latest: LivePoseResult | None = None
        self._camera_index = 0
        self._width = 640
        self._height = 480

    def configure(self, camera_index: int = 0, width: int = 640, height: int = 480) -> None:
        with self._lock:
            self._camera_index = int(camera_index)
            self._width = int(width)
            self._height = int(height)

    def activate(self) -> None:
        self._active.set()

    def deactivate(self) -> None:
        self._active.clear()
        with self._lock:
            self._latest = None

    def take_latest(self) -> LivePoseResult | None:
        with self._lock:
            result = self._latest
            self._latest = None
        return result

    def stop(self) -> None:
        self.requestInterruption()
        self._active.set()
        self.wait(5000)

    def run(self) -> None:  # noqa: C901  # pragma: no cover - coordinacion de recursos
        cap = None
        try:
            self.status_changed.emit("Preparando el modelo de pose en segundo plano...")
            import cv2
            import mediapipe as mp

            pose_module = mp.solutions.pose
            drawing = mp.solutions.drawing_utils
            with pose_module.Pose(
                model_complexity=0,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6,
            ) as pose:
                self.model_ready.emit()
                self.status_changed.emit("Modelo listo.")
                while not self.isInterruptionRequested():
                    if not self._active.wait(0.1):
                        if cap is not None:
                            cap.release()
                            cap = None
                        continue
                    if self.isInterruptionRequested():
                        break
                    if cap is None:
                        with self._lock:
                            camera_index, width, height = self._camera_index, self._width, self._height
                        if sys.platform == "win32":
                            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                            if not cap.isOpened():
                                cap.release()
                                cap = cv2.VideoCapture(camera_index)
                        else:
                            cap = cv2.VideoCapture(camera_index)
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        if not cap.isOpened():
                            self.status_changed.emit(f"No se pudo abrir la cámara {camera_index}.")
                            cap.release()
                            cap = None
                            self._active.clear()
                            continue
                        self.status_changed.emit(f"Cámara {camera_index} activa ({width} × {height}).")

                    ok, frame = cap.read()
                    if not ok:
                        self.status_changed.emit("No se pudo leer un fotograma de la cámara.")
                        time.sleep(0.05)
                        continue
                    frame = cv2.flip(frame, 1)
                    result = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    points = {}
                    confidence = {}
                    image_landmarks = result.pose_landmarks.landmark if result.pose_landmarks else None
                    world_landmarks = result.pose_world_landmarks.landmark if result.pose_world_landmarks else None
                    if image_landmarks is not None and world_landmarks is not None:
                        for index, name in enumerate(MEDIAPIPE_BODY_LANDMARKS):
                            visibility = float(getattr(image_landmarks[index], "visibility", 1.0))
                            confidence[name] = visibility
                            if visibility >= 0.5:
                                landmark = world_landmarks[index]
                                points[name] = [float(landmark.x), float(-landmark.y), float(-landmark.z)]
                        drawing.draw_landmarks(frame, result.pose_landmarks, pose_module.POSE_CONNECTIONS)
                    points.update(
                        {
                            "left_foot": points["left_foot_index"],
                            "right_foot": points["right_foot_index"],
                        }
                        if "left_foot_index" in points and "right_foot_index" in points
                        else {}
                    )
                    skeleton = SkeletonFrame(
                        points=points,
                        confidence=confidence,
                        timestamp=time.monotonic(),
                        source="mediapipe_live",
                        length_unit="m_aproximado",
                    )
                    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    with self._lock:
                        self._latest = LivePoseResult(image_rgb=image_rgb, skeleton=skeleton)
        except Exception as exc:
            self.status_changed.emit(f"Procesamiento de cámara detenido: {exc}")
        finally:
            if cap is not None:
                cap.release()
