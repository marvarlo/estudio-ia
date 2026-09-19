"""Adaptador TTS contra Lemonade Server (MOSS-TTS-Local, OpenAI Speech-compatible).

Payload identico al verificado en scripts/create_audio_local.py del skill
historias-fantasia: POST {base}/audio/speech con {model, input, voice},
Accept: audio/mpeg.
"""
from __future__ import annotations

import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.tts import TTSRequest, TTSResult

DEFAULT_MODEL = "MOSS-TTS-Local"


class LemonadeTTSAdapter:
    def __init__(self, base_url: str, model: str = DEFAULT_MODEL, timeout: float = 120.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        payload = {
            "model": request.model or self._model,
            "input": request.text,
            "voice": request.voice_id,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/audio/speech",
                json=payload,
                headers={"Accept": "audio/mpeg"},
            )
            response.raise_for_status()
            audio_bytes = response.content
        return TTSResult(audio_bytes=audio_bytes, provider="lemonade", model=payload["model"])

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/models")
                response.raise_for_status()
                data = response.json()
            model_ids = {m.get("id") for m in data.get("data", [])}
            latency_ms = (time.perf_counter() - start) * 1000
            if self._model in model_ids:
                return ProviderHealth(ok=True, detail=f"Modelo '{self._model}' descargado y listo", latency_ms=latency_ms)
            return ProviderHealth(ok=True, detail=f"Servidor accesible; '{self._model}' no listado", latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, detail=f"No se pudo contactar Lemonade Server en {self._base_url}: {exc}")
