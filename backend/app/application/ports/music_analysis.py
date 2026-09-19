"""Puerto: analizar estructura musical (BPM, tonalidad, secciones, beats)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class MusicAnalysisResult:
    bpm: float | None
    key: str | None
    sections: list[dict]  # [{"kind": "coro", "start": 12.0, "end": 28.0}, ...]
    # Timestamps (segundos) de cada beat detectado -- usado para "cortar en
    # el beat" en el videoclip animado (fase 5) en vez de ventanas fijas de
    # 8s a ciegas. Vacio si el analisis no pudo determinar beats (ver
    # LibrosaMusicAnalysisAdapter).
    beats: list[float] = field(default_factory=list)


class MusicAnalysisPort(Protocol):
    async def analyze(self, audio_path: Path) -> MusicAnalysisResult: ...
