"""Procesamiento MediaPipe de fotogramas enviados por el navegador."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any

from puce_mocap.freemocap_session import MEDIAPIPE_BODY_LANDMARKS
from puce_mocap.skeleton_frame import SkeletonFrame


@dataclass(frozen=True)
class BrowserPoseFrame:
    skeleton: SkeletonFrame
    landmarks: list[dict[str, float]]
    processing_ms: float


class BrowserPoseProcessor:
    """Mantiene una instancia MediaPipe para analizar imágenes del cliente web."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pose: Any | None = None

    def close(self) -> None:
        with self._lock:
            if self._pose is not None:
                self._pose.close()
                self._pose = None

    def process_jpeg(self, image_bytes: bytes) -> BrowserPoseFrame:
        if not image_bytes:
            raise ValueError("El fotograma recibido está vacío.")

        import cv2
        import mediapipe as mp
        import numpy as np

        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("El navegador envió una imagen no válida.")

        started = time.perf_counter()
        with self._lock:
            if self._pose is None:
                self._pose = mp.solutions.pose.Pose(
                    model_complexity=0,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6,
                )
            result = self._pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        points: dict[str, list[float]] = {}
        confidence: dict[str, float] = {}
        landmarks: list[dict[str, float]] = []
        image_landmarks = result.pose_landmarks.landmark if result.pose_landmarks else None
        world_landmarks = result.pose_world_landmarks.landmark if result.pose_world_landmarks else None
        if image_landmarks is not None:
            landmarks = [
                {
                    "x": float(landmark.x),
                    "y": float(landmark.y),
                    "visibility": float(getattr(landmark, "visibility", 1.0)),
                }
                for landmark in image_landmarks
            ]
        if image_landmarks is not None and world_landmarks is not None:
            for index, name in enumerate(MEDIAPIPE_BODY_LANDMARKS):
                image_landmark = image_landmarks[index]
                inside_frame = (
                    -0.02 <= float(image_landmark.x) <= 1.02
                    and -0.02 <= float(image_landmark.y) <= 1.02
                )
                visibility = float(getattr(image_landmark, "visibility", 1.0)) if inside_frame else 0.0
                confidence[name] = visibility
                if visibility >= 0.5:
                    landmark = world_landmarks[index]
                    points[name] = [float(landmark.x), float(-landmark.y), float(-landmark.z)]
        if "left_foot_index" in points and "right_foot_index" in points:
            points["left_foot"] = points["left_foot_index"]
            points["right_foot"] = points["right_foot_index"]

        timestamp = time.monotonic()
        return BrowserPoseFrame(
            skeleton=SkeletonFrame(
                points=points,
                confidence=confidence,
                timestamp=timestamp,
                source="navegador_mediapipe",
                length_unit="m_aproximado",
            ),
            landmarks=landmarks,
            processing_ms=(time.perf_counter() - started) * 1000.0,
        )
