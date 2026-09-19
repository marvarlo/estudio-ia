from __future__ import annotations

from fastapi import APIRouter, Depends

from app.adapters.inbound.api.deps import get_provider_registry
from app.adapters.inbound.api.schemas import ProviderHealthOut, ProviderOut
from app.application.use_cases.provider_queries import ListProvidersUseCase, TestProviderUseCase

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderOut])
def list_providers(registry=Depends(get_provider_registry)) -> list[ProviderOut]:
    summaries = ListProvidersUseCase(registry).execute()
    return [ProviderOut.from_domain(s) for s in summaries]


@router.post("/{provider_id}/test", response_model=ProviderHealthOut)
async def test_provider(provider_id: str, registry=Depends(get_provider_registry)) -> ProviderHealthOut:
    """Prueba de humo: el mismo boton 'Probar' descrito en la seccion 9 del
    doc de arquitectura. Para proveedores locales (Lemonade) golpea /models;
    para cloud, valida la API key con la llamada mas barata disponible."""
    health = await TestProviderUseCase(registry).execute(provider_id)
    return ProviderHealthOut.from_domain(health)
