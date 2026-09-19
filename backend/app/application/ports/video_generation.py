"""Puerto: imagen -> video (WAN 2.7 con lip-sync, Veo 3.1, Gemini Omni)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class VideoGenerationRequest:
    prompt: str
    image_path: Path | None = None
    driving_audio_path: Path | None = None  # para lip-sync real (WAN 2.7)
    duration_seconds: float = 5.0
    width: int = 1280
    height: int = 720


@dataclass
class VideoGenerationResult:
    video_bytes: bytes
    provider: str
    model: str


class VideoGenerationPort(Protocol):
    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult: ...
    async def health_check(self) -> "ProviderHealth": ...  # noqa: F821
