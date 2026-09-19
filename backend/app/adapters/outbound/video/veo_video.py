"""Adaptador de video contra Google Veo. Payload y flujo (crear operacion
long-running, poll, descargar) identicos a los verificados en
scripts/google_video.py del skill historias-fantasia. A diferencia de WAN,
Veo no recibe audio real como driving signal -- el clip sale mudo o con
audio inventado por el modelo; el use case reemplaza la pista despues con el
audio real de ElevenLabs/Lemonade via ffmpeg (ver replace_audio en el script
original, fuera de este adaptador -- responsabilidad del caso de uso)."""
from __future__ import annotations

import asyncio
import base64
import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.video_generation import VideoGenerationRequest, VideoGenerationResult

MODEL = "veo-3.1-lite-generate-preview"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
POLL_INTERVAL_SECONDS = 5.0


class VeoVideoAdapter:
    def __init__(self, api_key: str | None, model: str = MODEL, timeout: float = 120.0, poll_timeout: float = 600.0) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._poll_timeout = poll_timeout

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        if not self._api_key:
            raise RuntimeError("GOOGLE_API_KEY no configurada")
        if request.image_path is None:
            raise ValueError("Veo requiere image_path (primer frame)")

        duration_seconds = min(int(request.duration_seconds) or 8, 8)  # Veo tope 8s, ver script original
        image_b64 = base64.b64encode(request.image_path.read_bytes()).decode("utf-8")
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": request.prompt},
                        {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                    ],
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "VIDEO"],
                "videoConfig": {
                    "durationSeconds": duration_seconds,
                    "aspectRatio": "16:9" if request.width >= request.height else "9:16",
                    "resolution": "720p",
                },
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            url = f"{API_BASE}/models/{self._model}:generateContent"
            response = await client.post(url, params={"key": self._api_key}, json=payload)
            response.raise_for_status()
            data = response.json()

            operation = data.get("operation") or data.get("result") or data
            op_name = operation.get("name") if isinstance(operation, dict) else None
            if op_name:
                deadline = time.monotonic() + self._poll_timeout
                while True:
                    status_response = await client.get(f"{API_BASE}/{op_name}", params={"key": self._api_key})
                    status_response.raise_for_status()
                    status = status_response.json()
                    state = status.get("state") or status.get("status") or status.get("done")
                    if state in ("SUCCEEDED", True, "succeeded"):
                        video_bytes = await _download_video(client, status, self._api_key)
                        return VideoGenerationResult(video_bytes=video_bytes, provider="veo", model=self._model)
                    if state in ("FAILED", "failed"):
                        raise RuntimeError(f"Veo fallo al generar el video: {status}")
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"Veo no termino la operacion {op_name} dentro de {self._poll_timeout}s")
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)

            video_bytes = await _download_video(client, data, self._api_key)
        return VideoGenerationResult(video_bytes=video_bytes, provider="veo", model=self._model)

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, detail="Falta GOOGLE_API_KEY")
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{API_BASE}/models/{self._model}", params={"key": self._api_key})
                response.raise_for_status()
            return ProviderHealth(ok=True, detail=f"Modelo '{self._model}' accesible", latency_ms=(time.perf_counter() - start) * 1000)
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, detail=f"Error al validar Veo: {exc}")


async def _download_video(client: httpx.AsyncClient, response_data: dict, api_key: str) -> bytes:
    """Busca una URI o bytes base64 de video en varias formas posibles de
    respuesta -- la API de video generation todavia no tiene una unica forma
    documentada estable, ver _extract_uri_from_response/_extract_base64_from_response
    en google_video.py del skill original."""
    candidates = [response_data, response_data.get("video"), response_data.get("result"), response_data.get("output")]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key in ("videoUri", "uri", "downloadUrl", "url"):
            uri = candidate.get(key)
            if isinstance(uri, str):
                video_response = await client.get(uri, params={"key": api_key} if "generativelanguage" in uri else None)
                video_response.raise_for_status()
                return video_response.content
        for key in ("bytesBase64Encoded", "base64"):
            data = candidate.get(key)
            if isinstance(data, str):
                return base64.b64decode(data)
        videos = candidate.get("videos")
        if isinstance(videos, list) and videos:
            return await _download_video(client, videos[0] if isinstance(videos[0], dict) else {}, api_key)
    raise RuntimeError(f"Veo no devolvio un video util: {response_data}")
