"""Adaptador OpenAI-compatible contra el chat de Lemonade Server (local).

Endpoint y forma de payload iguales a las que ya usa
scripts/audit_production.py del skill historias-fantasia
(base http://localhost:13305/v1, chat completions estandar).
"""
from __future__ import annotations

import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.text_generation import (
    TextGenerationRequest,
    TextGenerationResult,
)

DEFAULT_MODEL = "gemma4-it-e4b-FLM"


class LemonadeTextAdapter:
    # 180s default: la generacion de canon/cast pide varios miles de tokens
    # JSON estructurados, y un modelo local (NPU/CPU) puede tardar bastante
    # mas que una llamada de chat corta -- el health_check usa su propio
    # cliente de 5s, no este timeout.
    def __init__(self, base_url: str, model: str = DEFAULT_MODEL, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.json_mode:
            # Best-effort: no todos los backends OpenAI-compatible locales
            # honran response_format, pero pasarlo no rompe los que no lo
            # soportan -- la robustez real ante JSON mal formado vive en el
            # parser del caso de uso (extract_json_object), no aca.
            payload["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        text = data["choices"][0]["message"]["content"]
        return TextGenerationResult(text=text, model=self._model, provider="lemonade")

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/models")
                response.raise_for_status()
                data = response.json()
            model_ids = {m.get("id") for m in data.get("data", [])}
            latency_ms = (time.perf_counter() - start) * 1000
            if self._model not in model_ids:
                return ProviderHealth(
                    ok=True,
                    detail=f"Servidor accesible ({len(model_ids)} modelos); '{self._model}' no esta entre ellos",
                    latency_ms=latency_ms,
                )
            return ProviderHealth(ok=True, detail=f"{len(model_ids)} modelos disponibles", latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo de red se reporta al panel, no se propaga
            return ProviderHealth(ok=False, detail=f"No se pudo contactar Lemonade Server en {self._base_url}: {exc}")
