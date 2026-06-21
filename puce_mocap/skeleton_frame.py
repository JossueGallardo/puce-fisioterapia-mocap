"""Contratos comunes para fuentes de esqueletos 3D."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class SkeletonFrame:
    points: Mapping[str, Sequence[float]]
    confidence: Mapping[str, float] = field(default_factory=dict)
    timestamp: float | None = None
    source: str = "unknown"
    length_unit: str = "sin_especificar"


class PoseFrameProvider(Protocol):
    @property
    def frame_count(self) -> int | None:
        ...

    def get_frame(self, index: int) -> SkeletonFrame:
        ...

    def __iter__(self) -> Iterator[SkeletonFrame]:
        ...
