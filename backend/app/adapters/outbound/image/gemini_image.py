"""Adaptador de imagen contra Gemini (Nano Banana Pro). Fase 0: solo
configuracion + health_check; generate() con soporte de imagenes de
referencia llega en la fase 2 (Storyboard), portando la logica ya verificada
de scripts/create_images.py del skill historias-fantasia."""
from __future__ import annotations

from app.application.ports.image_generation import (
    ImageGenerationRequest,
    ImageGenerationResult,
)
from app.application.ports.provider_health import ProviderHealth

DEFAULT_MODEL = "gemini-3.1-flash-image"  # Nano Banana Pro


class GeminiImageAdapter:
    def __init__(self, api_key: str | None, model: str = DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        raise NotImplementedError("GeminiImageAdapter.generate llega en la fase 2 (Storyboard)")

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(ok=False, detail="Falta GEMINI_API_KEY")
        return ProviderHealth(ok=True, detail="API key presente (generate() aun no implementado, fase 2)")
