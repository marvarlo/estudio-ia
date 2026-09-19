"""Adaptador de imagen contra Gemini (Nano Banana Pro). Payload y logica de
fallback entre modelos identicos a los verificados en
scripts/create_images.py del skill historias-fantasia: endpoint real
`models/{model}:generateContent` (nunca "interactions", que no existe),
`generationConfig.imageConfig` para aspect ratio/tamano, y soporte
multimodal (imagenes de referencia como `inline_data` antes del texto) para
mantener consistencia de personaje/escenario -- ver
references/consistencia_referencias_gemini.md del skill original.
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

API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3.1-flash-image"  # Nano Banana Pro
DEFAULT_FALLBACK_MODELS = ["gemini-3.1-flash-image", "gemini-3.1-flash-lite-image", "gemini-3-pro-image"]
DEFAULT_SIZE = "1K"


def _aspect_ratio_label(width: int, height: int) -> str:
    """Gemini pide un aspect ratio con nombre (ej. '16:9'), no ancho x alto
    en pixeles -- se resuelve al mas cercano de los presets conocidos."""
    ratio = width / height if height else 1.0
    presets = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:3": 4 / 3, "3:4": 3 / 4, "3:2": 3 / 2}
    return min(presets, key=lambda name: abs(presets[name] - ratio))


def _build_parts(request: ImageGenerationRequest) -> list[dict]:
    parts: list[dict] = []
    for ref_path in request.reference_images:
        parts.append(
            {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(ref_path.read_bytes()).decode()}}
        )
    parts.append({"text": request.prompt})
    return parts


class GeminiImageAdapter:
    def __init__(
        self,
        api_key: str | None,
        model: str = DEFAULT_MODEL,
        fallback_models: list[str] | None = None,
        timeout: float = 300.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._fallback_models = fallback_models or DEFAULT_FALLBACK_MODELS
        self._timeout = timeout

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada")
        parts = _build_parts(request)
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "imageConfig": {
                    "aspectRatio": _aspect_ratio_label(request.width, request.height),
                    "imageSize": DEFAULT_SIZE,
                }
            },
        }
        models = [request.model] if request.model else [self._model, *self._fallback_models]
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for candidate in dict.fromkeys(models):  # dedup conservando orden
                url = API_URL_TEMPLATE.format(model=candidate)
                try:
                    response = await client.post(url, params={"key": self._api_key}, json=payload)
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPError as exc:
                    last_error = exc
                    continue
                for candidate_resp in data.get("candidates", []):
                    for block in candidate_resp.get("content", {}).get("parts", []):
                        inline = block.get("inlineData") or block.get("inline_data")
                        if inline and inline.get("data"):
                            image_bytes = base64.b64decode(inline["data"])
                            return ImageGenerationResult(
                                image_bytes=image_bytes,
                                width=request.width,
                                height=request.height,
                                provider="gemini",
                                model=candidate,
                                seed=request.seed,
                            )
                last_error = RuntimeError(f"Gemini ({candidate}) respondio sin ningun part con inlineData")
        raise RuntimeError(f"No se pudo generar la imagen con Gemini. Ultimo error: {last_error}")

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, detail="Falta GEMINI_API_KEY")
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # GET a la metadata del modelo: confirma credenciales sin
                # gastar una generacion de imagen real.
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}"
                response = await client.get(url, params={"key": self._api_key})
                response.raise_for_status()
            return ProviderHealth(
                ok=True, detail=f"Modelo '{self._model}' accesible", latency_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, detail=f"Error al validar Gemini: {exc}")
