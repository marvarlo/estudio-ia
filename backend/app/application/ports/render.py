"""Puerto: render de composicion (sidecar Remotion) y utilidades de ffmpeg."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class RenderRequest:
    composition_id: str  # "Capitulo" | "MusicVideo" | "LyricsVideo" | "Karaoke"
    timeline: dict[str, Any]  # timeline.json ya resuelto
    output_path: Path


@dataclass
class RenderResult:
    output_path: Path
    duration_seconds: float


class RenderPort(Protocol):
    async def render(self, request: RenderRequest) -> RenderResult: ...
    async def concat(self, clips: list[Path], output_path: Path) -> RenderResult: ...
