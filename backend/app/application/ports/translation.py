"""Puerto: traducir prompts ES->EN (Lemonade translategemma, o el LLM configurado)."""
from __future__ import annotations

from typing import Protocol


class TranslationPort(Protocol):
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str: ...
