"""Puerto: audio -> palabras con tiempos (faster-whisper local, ElevenLabs Scribe)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class TranscribedWord:
    text: str
    start: float
    end: float
    probability: float
    suspect: bool = False


@dataclass
class TranscriptionResult:
    words: list[TranscribedWord]
    language: str
    raw_text: str


class TranscriptionPort(Protocol):
    async def transcribe(self, audio_path: Path, language: str | None = None) -> TranscriptionResult: ...
