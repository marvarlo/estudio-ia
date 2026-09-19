"""Puerto: texto -> audio. Cubre ElevenLabs (v3 con audio tags, text-to-dialogue
multi-voz) y Lemonade local (MOSS-TTS-Local, OpenAI Speech-compatible)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class TTSRequest:
    text: str
    voice_id: str
    model: str | None = None


@dataclass
class DialogueTurn:
    text: str
    voice_id: str


@dataclass
class TTSResult:
    audio_bytes: bytes
    provider: str
    model: str


class TTSPort(Protocol):
    async def synthesize(self, request: TTSRequest) -> TTSResult: ...
    async def health_check(self) -> "ProviderHealth": ...  # noqa: F821


class DialoguePort(Protocol):
    """Fusiona varias voces en un solo audio (ElevenLabs text-to-dialogue).
    Puerto separado de TTSPort porque no todo proveedor lo soporta."""

    async def synthesize_dialogue(self, turns: list[DialogueTurn]) -> TTSResult: ...
