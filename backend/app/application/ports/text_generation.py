"""Puerto: generacion de texto (escritura de canon/capitulos, LLM auxiliar)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TextGenerationRequest:
    prompt: str
    system: str | None = None
    max_tokens: int = 2000
    temperature: float = 0.7
    json_mode: bool = False


@dataclass
class TextGenerationResult:
    text: str
    model: str
    provider: str


class TextGenerationPort(Protocol):
    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult: ...
    async def health_check(self) -> "ProviderHealth": ...  # noqa: F821 (evita import circular)
