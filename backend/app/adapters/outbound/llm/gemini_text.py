"""Adaptador de texto contra Gemini (usado por GenerateCanon/GenerateCast en
la fase 1 cuando el usuario elige Gemini como proveedor de escritura en vez
de Lemonade local)."""
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
    def __init__(self, api_key: str | None, model: str = DEFAULT_MODEL, timeout: float = 120.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada")
        url = API_URL_TEMPLATE.format(model=self._model)
        parts = []
        if request.system:
            # Gemini no tiene un rol "system" separado en este endpoint
            # simple -- se antepone como contexto, igual que hace
            # audit_production.py del skill original.
            parts.append({"text": f"{request.system}\n\n{request.prompt}"})
        else:
            parts.append({"text": request.prompt})
        generation_config: dict = {"maxOutputTokens": request.max_tokens, "temperature": request.temperature}
        if request.json_mode:
            generation_config["responseMimeType"] = "application/json"
        payload = {"contents": [{"parts": parts}], "generationConfig": generation_config}
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
