"""Adaptador de video contra WAN 2.7 (DashScope/Alibaba), con lip-sync real
a partir del audio ya generado de la fila -- payload y flujo (crear tarea,
poll, descargar) identicos a los verificados en scripts/wan_video.py del
skill historias-fantasia."""
from __future__ import annotations

import asyncio
import base64
import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.video_generation import VideoGenerationRequest, VideoGenerationResult

CREATE_URL = "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
STATUS_URL_TEMPLATE = "https://dashscope-intl.aliyuncs.com/api/v1/tasks/{task_id}"
MODEL = "wan2.7-i2v"
DEFAULT_NEGATIVE_PROMPT = (
    "text on screen, subtitles, floating letters, extra arms, extra hands, body deformations, "
    "distorted faces, visual artifacts, irrelevant objects, glitches, duplicated characters"
)
POLL_INTERVAL_SECONDS = 5.0


def _file_to_data_uri(path, mime_type: str) -> str:
    return f"data:{mime_type};base64," + base64.b64encode(path.read_bytes()).decode("utf-8")


class WanVideoAdapter:
    def __init__(self, api_key: str | None, timeout: float = 300.0, poll_timeout: float = 900.0) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._poll_timeout = poll_timeout

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        if not self._api_key:
            raise RuntimeError("ALI_API_KEY no configurada")
        if request.image_path is None or request.driving_audio_path is None:
            raise ValueError("WAN 2.7 requiere image_path (primer frame) y driving_audio_path (lip-sync)")

        audio_suffix = request.driving_audio_path.suffix.lower()
        audio_mime = "audio/mp3" if audio_suffix == ".mp3" else "audio/wav"
        payload = {
            "model": MODEL,
            "input": {
                "prompt": request.prompt or "Anime-style character, synchronized narration with audio.",
                "negative_prompt": DEFAULT_NEGATIVE_PROMPT,
                "media": [
                    {"type": "first_frame", "url": _file_to_data_uri(request.image_path, "image/png")},
                    {"type": "driving_audio", "url": _file_to_data_uri(request.driving_audio_path, audio_mime)},
                ],
            },
            "parameters": {
                "resolution": "720P",
                "duration": max(1, round(request.duration_seconds)),
                "prompt_extend": True,
                "watermark": False,
                "consistency_mode": "strict",
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            create_response = await client.post(CREATE_URL, json=payload, headers=headers)
            create_response.raise_for_status()
            task_id = create_response.json()["output"]["task_id"]

            deadline = time.monotonic() + self._poll_timeout
            status_url = STATUS_URL_TEMPLATE.format(task_id=task_id)
            while True:
                status_response = await client.get(status_url, headers={"Authorization": f"Bearer {self._api_key}"})
                status_response.raise_for_status()
                data = status_response.json()
                status = data["output"]["task_status"]
                if status == "SUCCEEDED":
                    video_url = data["output"]["video_url"]
                    break
                if status == "FAILED":
                    reason = data.get("output", {}).get("message") or data.get("output", {}).get("error_message") or "sin detalle"
                    raise RuntimeError(f"WAN 2.7 fallo al generar el video: {reason}")
                if time.monotonic() > deadline:
                    raise TimeoutError(f"WAN 2.7 no termino la tarea {task_id} dentro de {self._poll_timeout}s")
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

            video_response = await client.get(video_url)
            video_response.raise_for_status()
            video_bytes = video_response.content

        return VideoGenerationResult(video_bytes=video_bytes, provider="wan", model=MODEL)

    async def health_check(self) -> ProviderHealth:
        # DashScope no documenta un endpoint barato de "ping" para este
        # servicio -- a diferencia de Lemonade/Gemini, esto solo confirma
        # que la clave esta presente, no que sea valida ni que el servicio
        # responda.
        if not self._api_key:
            return ProviderHealth(ok=False, detail="Falta ALI_API_KEY")
        return ProviderHealth(ok=True, detail="API key presente (sin endpoint de prueba barato disponible)")
