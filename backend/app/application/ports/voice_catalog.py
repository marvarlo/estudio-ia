"""Puerto: buscar/previsualizar voces (ElevenLabs Voice Library, MOSS-VoiceGen)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class VoiceCandidate:
    voice_id: str
    nombre: str
    descripcion: str = ""
    preview_url: str | None = None


class VoiceCatalogPort(Protocol):
    async def search(self, query: str) -> list[VoiceCandidate]: ...
