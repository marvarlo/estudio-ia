"""Dependencias de FastAPI. Los singletons (engine, repository, registry) se
crean una vez en el lifespan de main.py y quedan en `app.state`; estas
funciones solo los exponen a los routers via Depends()."""
from __future__ import annotations

from fastapi import Request

from app.application.ports.repository import ProjectRepositoryPort
from app.config.provider_registry import ProviderRegistry


def get_repository(request: Request) -> ProjectRepositoryPort:
    return request.app.state.repository


def get_provider_registry(request: Request) -> ProviderRegistry:
    return request.app.state.provider_registry
