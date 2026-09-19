"""Adaptador de imagen contra Lemonade Server (Flux2 / Qwen Image, local).

Payload y endpoint identicos a los verificados en
scripts/create_images_local.py del skill historias-fantasia: POST
{base}/images/generations con {model, prompt, size, response_format:
"b64_json", steps, cfg_scale, seed}, con /images y /text-to-image como
fallback si el primero da 404/405 (algunos backends locales exponen otra ruta).
"""
from __future__ import annotations

import base64
import time

import httpx

from app.application.ports.image_generation import (
    ImageGenerationRequest,
    ImageGenerationResult,
)
from app.application.ports.provider_health import ProviderHealth

DEFAULT_MODEL = "Flux-2-Klein-4B"
# steps=4/cfg_scale=1 es el preset "flux2" verificado -- ver
# references/generacion_local_lemonade.md del skill original. Qwen Image
# necesita steps 20-36 / cfg_scale 2.5-7.2 en cambio.
DEFAULT_STEPS = 4
DEFAULT_CFG_SCALE = 1.0
DEFAULT_SEED = 1618034

_ENDPOINT_SUFFIXES = ("/images/generations", "/images", "/text-to-image")


def _extract_image_bytes(response_json: dict) -> bytes:
    data = response_json.get("data")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and first.get("b64_json"):
            return base64.b64decode(first["b64_json"])
    for key in ("image", "image_base64", "b64_json"):
        value = response_json.get(key)
        if isinstance(value, str) and value:
            return base64.b64decode(value)
    raise ValueError(f"Respuesta inesperada del servidor de imagenes: {response_json!r}")


class LemonadeImageAdapter:
    def __init__(self, base_url: str, model: str = DEFAULT_MODEL, timeout: float = 300.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        payload = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "size": f"{request.width}x{request.height}",
            "response_format": "b64_json",
            "steps": request.steps if request.steps is not None else DEFAULT_STEPS,
            "cfg_scale": request.cfg_scale if request.cfg_scale is not None else DEFAULT_CFG_SCALE,
            "seed": request.seed if request.seed is not None else DEFAULT_SEED,
        }
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for suffix in _ENDPOINT_SUFFIXES:
                try:
                    response = await client.post(f"{self._base_url}{suffix}", json=payload)
                    if response.status_code in (404, 405):
                        continue
                    response.raise_for_status()
                    image_bytes = _extract_image_bytes(response.json())
                    return ImageGenerationResult(
                        image_bytes=image_bytes,
                        width=request.width,
                        height=request.height,
                        provider="lemonade",
                        model=payload["model"],
                        seed=payload["seed"],
                    )
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                except httpx.HTTPError as exc:
                    last_error = exc
        # str(last_error) puede venir vacio para ciertas excepciones de httpx
        # (ej. ReadTimeout sin mensaje) -- verificado en vivo mas de una vez,
        # dejando "Ultimo error: " sin nada util despues. Cae al nombre de
        # la clase cuando pasa, mismo criterio que in_process_job_queue.py.
        detail = str(last_error) or (type(last_error).__name__ if last_error else "sin detalle")
        raise RuntimeError(f"No se pudo generar la imagen en ningun endpoint de {self._base_url}. Ultimo error: {detail}")

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
