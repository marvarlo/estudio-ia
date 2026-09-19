"""Casos de uso del panel de proveedores: listar el registro y ejecutar la
prueba de humo de un proveedor puntual (boton 'Probar' del panel, seccion 9
del doc de arquitectura)."""
from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.provider_health import ProviderHealth
from app.config.provider_registry import ProviderDescriptor, ProviderRegistry


@dataclass
class ProviderSummary:
    id: str
    name: str
    kind: str
    capabilities: list[str]
    configured: bool


class ListProvidersUseCase:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def execute(self) -> list[ProviderSummary]:
        return [
            ProviderSummary(id=d.id, name=d.name, kind=d.kind, capabilities=d.capabilities, configured=d.configured)
            for d in self._registry.list()
        ]


class TestProviderUseCase:
    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    async def execute(self, provider_id: str) -> ProviderHealth:
        return await self._registry.test(provider_id)
