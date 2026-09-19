"""Adaptador TTS contra ElevenLabs. Fase 0: solo configuracion + health_check
(consulta /v1/user, que no genera audio ni consume creditos de sintesis).
synthesize() con audio tags/eleven_v3 llega en la fase 2 junto a create_audio.py."""
from __future__ import annotations

import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.tts import TTSRequest, TTSResult

API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_multilingual_v2"


class ElevenLabsTTSAdapter:
    def __init__(self, api_key: str | None, model: str = DEFAULT_MODEL, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        raise NotImplementedError("ElevenLabsTTSAdapter.synthesize llega en la fase 2 (Storyboard)")

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, detail="Falta ELEVENLABS_API_KEY")
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{API_BASE}/user", headers={"xi-api-key": self._api_key})
                response.raise_for_status()
                data = response.json()
            latency_ms = (time.perf_counter() - start) * 1000
            tier = data.get("subscription", {}).get("tier", "?")
            return ProviderHealth(ok=True, detail=f"API key valida (plan: {tier})", latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, detail=f"Error al validar la API key: {exc}")
