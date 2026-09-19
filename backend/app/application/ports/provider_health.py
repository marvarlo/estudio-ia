"""Contrato comun de salud/prueba de humo para cualquier adaptador de
proveedor -- lo que el boton 'Probar' del panel de proveedores invoca."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderHealth:
    ok: bool
    detail: str
    latency_ms: float | None = None


class HealthCheckable(Protocol):
    async def health_check(self) -> ProviderHealth: ...
