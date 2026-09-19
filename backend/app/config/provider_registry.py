"""ProviderRegistry: la cara de codigo del panel de proveedores (seccion 9
del doc de arquitectura). Los casos de uso piden una capacidad ('un
generador de imagenes'), nunca un proveedor por nombre -- ver
application/use_cases/list_providers.py y test_provider.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adapters.outbound.image.gemini_image import GeminiImageAdapter
from app.adapters.outbound.image.lemonade_image import LemonadeImageAdapter
from app.adapters.outbound.llm.gemini_text import GeminiTextAdapter
from app.adapters.outbound.llm.lemonade_text import LemonadeTextAdapter
from app.adapters.outbound.tts.elevenlabs_tts import ElevenLabsTTSAdapter
from app.adapters.outbound.tts.lemonade_tts import LemonadeTTSAdapter
from app.adapters.outbound.video.omni_video import GeminiOmniVideoAdapter
from app.adapters.outbound.video.veo_video import VeoVideoAdapter
from app.adapters.outbound.video.wan_video import WanVideoAdapter
from app.application.ports.provider_health import ProviderHealth
from app.config.settings import Settings


@dataclass
class ProviderDescriptor:
    id: str
    name: str
    kind: str  # "local" | "cloud"
    capabilities: list[str]
    configured: bool
    adapter: Any


class ProviderRegistry:
    """Registro en memoria, poblado al levantar la app. Ampliar esta lista es
    el unico lugar que toca codigo al agregar un proveedor nuevo -- todo lo
    demas (panel, casos de uso) itera sobre `list()`."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._providers: dict[str, ProviderDescriptor] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._add(
            "lemonade-text", "Lemonade Server (chat local)", "local", ["text"],
            configured=True, adapter=LemonadeTextAdapter(self._settings.lemonade_base_url),
        )
        self._add(
            "lemonade-image", "Lemonade Server (Flux2 / Qwen Image)", "local", ["image"],
            configured=True, adapter=LemonadeImageAdapter(self._settings.lemonade_base_url),
        )
        self._add(
            "lemonade-tts", "Lemonade Server (MOSS-TTS-Local)", "local", ["tts"],
            configured=True, adapter=LemonadeTTSAdapter(self._settings.lemonade_base_url),
        )
        self._add(
            "gemini", "Google Gemini (texto + Nano Banana Pro)", "cloud", ["text", "image"],
            configured=self._settings.gemini_api_key is not None,
            adapter=GeminiTextAdapter(self._settings.gemini_api_key),
        )
        self._add(
            "gemini-image", "Google Gemini (imagen)", "cloud", ["image"],
            configured=self._settings.gemini_api_key is not None,
            adapter=GeminiImageAdapter(self._settings.gemini_api_key),
        )
        self._add(
            "elevenlabs", "ElevenLabs", "cloud", ["tts", "voice_design"],
            configured=self._settings.elevenlabs_api_key is not None,
            adapter=ElevenLabsTTSAdapter(self._settings.elevenlabs_api_key),
        )
        self._add(
            "wan-video", "WAN 2.7 (DashScope, lip-sync)", "cloud", ["video_lipsync"],
            configured=self._settings.ali_api_key is not None,
            adapter=WanVideoAdapter(self._settings.ali_api_key),
        )
        self._add(
            "veo-video", "Google Veo 3.1", "cloud", ["video_i2v"],
            configured=self._settings.google_api_key is not None,
            adapter=VeoVideoAdapter(self._settings.google_api_key),
        )
        self._add(
            "gemini-omni-video", "Gemini Omni (video, experimental)", "cloud", ["video_i2v"],
            configured=self._settings.google_api_key is not None,
            adapter=GeminiOmniVideoAdapter(self._settings.google_api_key),
        )

    def _add(self, id_: str, name: str, kind: str, capabilities: list[str], *, configured: bool, adapter: Any) -> None:
        self._providers[id_] = ProviderDescriptor(id_, name, kind, capabilities, configured, adapter)

    def list(self) -> list[ProviderDescriptor]:
        return list(self._providers.values())

    def get(self, provider_id: str) -> ProviderDescriptor | None:
        return self._providers.get(provider_id)

    async def test(self, provider_id: str) -> ProviderHealth:
        descriptor = self.get(provider_id)
        if descriptor is None:
            return ProviderHealth(ok=False, detail="Proveedor desconocido")
        if not descriptor.configured:
            return ProviderHealth(ok=False, detail="Falta configurar credenciales (API key)")
        return await descriptor.adapter.health_check()
