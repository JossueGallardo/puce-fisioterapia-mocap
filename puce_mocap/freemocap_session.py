"""Carga ligera de esqueletos procesados por FreeMoCap sin importar skellytracker."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import numpy as np

from puce_mocap.skeleton_frame import SkeletonFrame


MEDIAPIPE_BODY_LANDMARKS = (
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", "right_eye",
    "right_eye_outer", "left_ear", "right_ear", "mouth_left", "mouth_right", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist", "left_pinky",
    "right_pinky", "left_index", "right_index", "left_thumb", "right_thumb", "left_hip",
    "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle", "left_heel",
    "right_heel", "left_foot_index", "right_foot_index",
)


class FreeMoCapSessionProvider:
    """Expone cada frame de `*_body_3d_xyz.npy` con nombres MediaPipe estables."""

    def __init__(self, recording_folder: str | Path, length_unit: str = "sin_especificar"):
        self.recording_folder = Path(recording_folder)
        output = self.recording_folder / "output_data"
        candidates = sorted(output.glob("*_body_3d_xyz.npy"))
        if not candidates:
            raise FileNotFoundError(f"No se encontró output_data/*_body_3d_xyz.npy en {self.recording_folder}.")
        self.data_path = candidates[0]
        self._data = np.load(self.data_path, mmap_mode="r")
        if self._data.ndim != 3 or self._data.shape[1:] != (33, 3):
            raise ValueError(
                f"El esqueleto debe tener forma [frames, 33, 3]; se recibio {tuple(self._data.shape)}."
            )
        self.length_unit = str(length_unit).strip() or "sin_especificar"
        self._timestamps = self._load_timestamps()

    @property
    def frame_count(self) -> int:
        return int(self._data.shape[0])

    def _load_timestamps(self) -> np.ndarray | None:
        timestamp_dir = self.recording_folder / "synchronized_videos" / "timestamps"
        arrays = []
        for path in sorted(timestamp_dir.glob("*.npy")):
            values = np.asarray(np.load(path), dtype=float).reshape(-1)
            if len(values) >= self.frame_count:
                arrays.append(values[: self.frame_count])
        if not arrays:
            return None
        return np.nanmean(np.vstack(arrays), axis=0)

    def get_frame(self, index: int) -> SkeletonFrame:
        if not 0 <= index < self.frame_count:
            raise IndexError(f"Frame fuera de rango: {index}.")
        frame = np.asarray(self._data[index], dtype=float)
        points = {}
        confidence = {}
        for marker_index, name in enumerate(MEDIAPIPE_BODY_LANDMARKS):
            point = frame[marker_index]
            valid = bool(np.all(np.isfinite(point)))
            confidence[name] = 1.0 if valid else 0.0
            if valid:
                points[name] = point.tolist()
        timestamp = index / 30.0 if self._timestamps is None else float(self._timestamps[index])
        return SkeletonFrame(
            points=points,
            confidence=confidence,
            timestamp=timestamp,
            source="freemocap_session",
            length_unit=self.length_unit,
        )

    def __iter__(self) -> Iterator[SkeletonFrame]:
        for index in range(self.frame_count):
            yield self.get_frame(index)
