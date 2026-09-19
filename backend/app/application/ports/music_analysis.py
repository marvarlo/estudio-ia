"""Puerto: analizar estructura musical (BPM, tonalidad, secciones)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class MusicAnalysisResult:
    bpm: float | None
    key: str | None
    sections: list[dict]  # [{"kind": "coro", "start": 12.0, "end": 28.0}, ...]


class MusicAnalysisPort(Protocol):
    async def analyze(self, audio_path: Path) -> MusicAnalysisResult: ...
