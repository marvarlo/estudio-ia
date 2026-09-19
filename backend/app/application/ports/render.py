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
    # Carpeta que el sidecar sirve como "public dir" de Remotion (staticFile) --
    # las rutas de imagen/audio/video dentro de `timeline` son RELATIVAS a esta
    # carpeta, igual que build_scenes.py ya las generaba relativas a
    # `capitulo-N/assets/`. Ver render/remotion.config.ts.
    public_dir: Path


@dataclass
class RenderResult:
    output_path: Path
    duration_seconds: float


class RenderPort(Protocol):
    async def render(self, request: RenderRequest) -> RenderResult: ...
    async def concat(self, clips: list[Path], output_path: Path) -> RenderResult: ...
