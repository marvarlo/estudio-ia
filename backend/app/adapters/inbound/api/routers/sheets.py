from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import get_provider_registry, get_repository, resolve_adapter
from app.adapters.inbound.api.schemas import AssetOut, SheetGenerateRequest
from app.application.use_cases.reference_sheets import GenerateCharacterSheetUseCase, GenerateLocationSheetUseCase

router = APIRouter(tags=["sheets"])


@router.post("/api/characters/{character_id}/sheet:generate", response_model=AssetOut)
async def generate_character_sheet(
    character_id: str,
    payload: SheetGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
) -> AssetOut:
    image_port = resolve_adapter(registry, payload.provider_id)
    try:
        asset = await GenerateCharacterSheetUseCase(repository, image_port).execute(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AssetOut.from_domain(asset)


@router.post("/api/locations/{location_id}/sheet:generate", response_model=AssetOut)
async def generate_location_sheet(
    location_id: str,
    payload: SheetGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
) -> AssetOut:
    image_port = resolve_adapter(registry, payload.provider_id)
    try:
        asset = await GenerateLocationSheetUseCase(repository, image_port).execute(location_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AssetOut.from_domain(asset)
