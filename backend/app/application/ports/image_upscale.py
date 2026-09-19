"""Puerto: ampliar una imagen ya generada (ej. RealESRGAN-x4plus-anime local)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ImageUpscaleRequest:
    image_bytes: bytes
    scale: int = 2
    model: str | None = None


@dataclass
class ImageUpscaleResult:
    image_bytes: bytes
    width: int
    height: int


class ImageUpscalePort(Protocol):
    async def upscale(self, request: ImageUpscaleRequest) -> ImageUpscaleResult: ...
