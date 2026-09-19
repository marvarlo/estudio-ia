"""Dependencias de FastAPI. Los singletons (engine, repository, registry) se
crean una vez en el lifespan de main.py y quedan en `app.state`; estas
funciones solo los exponen a los routers via Depends()."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.application.ports.repository import ProjectRepositoryPort
from app.config.provider_registry import ProviderRegistry
from app.config.settings import Settings


def get_repository(request: Request) -> ProjectRepositoryPort:
    return request.app.state.repository


def get_provider_registry(request: Request) -> ProviderRegistry:
    return request.app.state.provider_registry


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def resolve_adapter(registry: ProviderRegistry, provider_id: str) -> Any:
    """Resuelve el adaptador configurado para `provider_id`, o 400 con un
    mensaje claro -- los casos de uso de generacion (canon, cast, fichas)
    reciben el adaptador ya resuelto, nunca el id crudo."""
    descriptor = registry.get(provider_id)
    if descriptor is None:
        raise HTTPException(status_code=400, detail=f"Proveedor desconocido: {provider_id}")
    if not descriptor.configured:
        raise HTTPException(status_code=400, detail=f"El proveedor '{provider_id}' no esta configurado (falta API key)")
    return descriptor.adapter
