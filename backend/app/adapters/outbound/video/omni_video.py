"""Adaptador de video contra Gemini Omni. EXPERIMENTAL: portado de
scripts/omni_video.py del skill historias-fantasia, que documenta esta API
como "nueva, verificada solo contra documentacion publica de Google, no
contra llamadas reales confirmadas" -- ese mismo caveat aplica aca sin
cambios. En particular, el endpoint `/v1beta/interactions` NO es el mismo
que create_images.py usa para imagenes (`/v1beta/models/{model}:generateContent`,
verificado real): esa discrepancia ya existia en el script original y no se
"corrigio" aca por no tener forma de confirmar cual es correcta para video
sin una llamada real. Antes de generar un capitulo entero con este
proveedor, probar una sola fila primero."""
from __future__ import annotations

import base64
import time

import httpx

from app.application.ports.provider_health import ProviderHealth
from app.application.ports.video_generation import VideoGenerationRequest, VideoGenerationResult

OMNI_MODEL = "gemini-omni-1.1-flash"
OMNI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _resolve_aspect_and_resolution(width: int, height: int) -> tuple[str, str]:
    aspect_ratio = "16:9" if width >= height else "9:16"
    long_side = max(width, height)
    if long_side <= 640:
        resolution = "360p"
    elif long_side <= 1280:
        resolution = "720p"
    elif long_side <= 1920:
        resolution = "1080p"
    else:
        resolution = "4k"
    return aspect_ratio, resolution


class GeminiOmniVideoAdapter:
    def __init__(self, api_key: str | None, timeout: float = 300.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        if not self._api_key:
            raise RuntimeError("GOOGLE_API_KEY no configurada")
        aspect_ratio, resolution = _resolve_aspect_and_resolution(request.width, request.height)

        if request.image_path is not None:
            input_payload = [
                {
                    "type": "image",
                    "data": base64.b64encode(request.image_path.read_bytes()).decode("utf-8"),
                    "mime_type": "image/png",
                },
                {"type": "text", "text": request.prompt},
            ]
        else:
            input_payload = request.prompt

        payload = {
            "model": OMNI_MODEL,
            "input": input_payload,
            "response_format": {"type": "video", "aspect_ratio": aspect_ratio, "resolution": resolution},
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(OMNI_ENDPOINT, params={"key": self._api_key}, json=payload)
            response.raise_for_status()
            data = response.json()

        video_bytes = _extract_video_bytes(data)
        return VideoGenerationResult(video_bytes=video_bytes, provider="gemini-omni", model=OMNI_MODEL)

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, detail="Falta GOOGLE_API_KEY")
        return ProviderHealth(
            ok=True,
            detail="API key presente -- EXPERIMENTAL: este endpoint no esta confirmado contra la API real, probar con --escena antes de un capitulo entero",
        )


def _extract_video_bytes(response: dict) -> bytes:
    """Tolera mas de una forma de respuesta -- ver _find_video_content_item en
    omni_video.py del skill original, mismo motivo (API nueva y no
    confirmada)."""
    for step in reversed(response.get("steps") or []):
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        for item in step.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "video" and item.get("data"):
                return base64.b64decode(item["data"])
    output = response.get("output")
    if isinstance(output, dict) and output.get("data"):
        return base64.b64decode(output["data"])
    raise RuntimeError(f"Gemini Omni no devolvio un video reconocible: {response}")
