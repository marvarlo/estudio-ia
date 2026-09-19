"""Adaptador de texto contra Gemini. Fase 0: solo configuracion + health_check
(valida que la API key este presente y que el modelo responda a una llamada
minima). generate() completo, incluyendo tool-use y JSON estructurado, llega
en la fase 1 junto con los casos de uso de escritura (GenerateCanon, etc.)."""
from __future__ import annotations

import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.text_generation import (
    TextGenerationRequest,
    TextGenerationResult,
)

DEFAULT_MODEL = "gemini-2.5-flash"
API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiTextAdapter:
    def __init__(self, api_key: str | None, model: str = DEFAULT_MODEL, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada")
        url = API_URL_TEMPLATE.format(model=self._model)
        payload = {"contents": [{"parts": [{"text": request.prompt}]}]}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, params={"key": self._api_key}, json=payload)
            response.raise_for_status()
            data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return TextGenerationResult(text=text, model=self._model, provider="gemini")

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, detail="Falta GEMINI_API_KEY")
        start = time.perf_counter()
        try:
            request = TextGenerationRequest(prompt="ping", max_tokens=1)
            await self.generate(request)
            return ProviderHealth(ok=True, detail="Respondio correctamente", latency_ms=(time.perf_counter() - start) * 1000)
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, detail=f"Error al llamar a Gemini: {exc}")
