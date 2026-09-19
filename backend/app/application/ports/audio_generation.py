"""Puerto: generar SFX o musica de fondo (Lemonade ThinkSound-SFX / ACE-Step)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class AudioGenerationRequest:
    prompt: str
    duration_seconds: float = 5.0


@dataclass
class AudioGenerationResult:
    audio_bytes: bytes
    provider: str
    model: str


class AudioGenerationPort(Protocol):
    async def generate(self, request: AudioGenerationRequest) -> AudioGenerationResult: ...
