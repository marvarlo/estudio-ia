"""Puerto: inspeccionar un archivo de medios (duracion, resolucion) -- ffprobe."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class MediaInfo:
    duration_seconds: float | None
    width: int | None = None
    height: int | None = None


class MediaProbePort(Protocol):
    def probe(self, path: Path) -> MediaInfo: ...
