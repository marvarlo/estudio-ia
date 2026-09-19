"""Dependencias de FastAPI. Los singletons (engine, repository, registry,
cola de jobs) se crean una vez en el lifespan de main.py y quedan en
`app.state`; estas funciones solo los exponen a los routers via Depends()."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.adapters.outbound.jobs.in_process_job_queue import InProcessJobQueue
from app.adapters.outbound.media.ffprobe_probe import FfprobeMediaProbe
from app.application.ports.job_queue import JobQueuePort
from app.application.ports.media_probe import MediaProbePort
from app.application.ports.render import RenderPort
from app.application.ports.repository import ProjectRepositoryPort
from app.application.use_cases.generate_shot_image import GenerateShotImageUseCase
from app.application.use_cases.generate_shot_video import GenerateShotVideoUseCase
from app.application.use_cases.render_chapter import RenderChapterUseCase
from app.config.provider_registry import ProviderRegistry
from app.config.settings import Settings

# Los unicos proveedores que aceptan imagenes de referencia hoy -- ver
# app/application/use_cases/generate_shot_image.py. Lista explicita en vez
# de inferirla de `kind` ("local"/"cloud") porque esa distincion no siempre
# va a coincidir (un proveedor cloud local-first futuro podria no soportar
# referencias tampoco).
_IMAGE_PROVIDERS_WITH_REFERENCES = {"gemini-image", "gemini"}
# Unico proveedor de video con lip-sync real (recibe el audio como driving
# signal) -- Veo/Omni no aceptan audio de referencia.
_VIDEO_PROVIDERS_REQUIRING_AUDIO = {"wan-video"}


def get_repository(request: Request) -> ProjectRepositoryPort:
    return request.app.state.repository


def get_provider_registry(request: Request) -> ProviderRegistry:
    return request.app.state.provider_registry


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_job_queue(request: Request) -> JobQueuePort:
    return request.app.state.job_queue


def get_media_probe(request: Request) -> MediaProbePort:
    return request.app.state.media_probe


def get_render_port(request: Request) -> RenderPort:
    return request.app.state.render_port


def resolve_adapter(registry: ProviderRegistry, provider_id: str) -> Any:
    """Resuelve el adaptador configurado para `provider_id`, o 400 con un
    mensaje claro -- los casos de uso de generacion (canon, cast, fichas,
    shots) reciben el adaptador ya resuelto, nunca el id crudo."""
    descriptor = registry.get(provider_id)
    if descriptor is None:
        raise HTTPException(status_code=400, detail=f"Proveedor desconocido: {provider_id}")
    if not descriptor.configured:
        raise HTTPException(status_code=400, detail=f"El proveedor '{provider_id}' no esta configurado (falta API key)")
    return descriptor.adapter


def build_image_use_case(registry: ProviderRegistry, repository: ProjectRepositoryPort, provider_id: str) -> GenerateShotImageUseCase:
    adapter = resolve_adapter(registry, provider_id)
    return GenerateShotImageUseCase(repository, adapter, supports_references=provider_id in _IMAGE_PROVIDERS_WITH_REFERENCES)


def build_video_use_case(
    registry: ProviderRegistry, repository: ProjectRepositoryPort, media_probe: MediaProbePort, provider_id: str
) -> GenerateShotVideoUseCase:
    adapter = resolve_adapter(registry, provider_id)
    return GenerateShotVideoUseCase(repository, adapter, media_probe, requires_audio=provider_id in _VIDEO_PROVIDERS_REQUIRING_AUDIO)


def build_render_use_case(
    repository: ProjectRepositoryPort, render_port: RenderPort, media_probe: MediaProbePort
) -> RenderChapterUseCase:
    return RenderChapterUseCase(repository, render_port, media_probe)
