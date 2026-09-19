"""Puerto: separar un audio musical en stems (Demucs local, o una API)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class SeparationResult:
    stems: dict[str, Path]  # ej. {"vocals": ..., "drums": ..., "instrumental": ...}


class SourceSeparationPort(Protocol):
    async def separate(self, audio_path: Path) -> SeparationResult: ...
