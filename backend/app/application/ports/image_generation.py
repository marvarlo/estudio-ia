"""Puerto: texto/imagen(es)-de-referencia -> imagen. Cubre tanto Gemini (Nano
Banana Pro, con referencias) como Lemonade local (Flux2/Qwen, sin referencias
-- ver references/generacion_local_lemonade.md del skill original)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class ImageGenerationRequest:
    prompt: str
    negative_prompt: str = ""
    width: int = 1280
    height: int = 720
    reference_images: list[Path] = field(default_factory=list)
    seed: int | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    model: str | None = None


@dataclass
class ImageGenerationResult:
    image_bytes: bytes
    width: int
    height: int
    provider: str
    model: str
    seed: int | None = None


class ImageGenerationPort(Protocol):
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult: ...
    async def health_check(self) -> "ProviderHealth": ...  # noqa: F821
