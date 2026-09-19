from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.adapters.inbound.api.deps import get_repository
from app.adapters.inbound.api.schemas import ShotOut, ShotWriteRequest
from app.application.use_cases.shot_editing import DeleteShotUseCase, ShotInput, UpdateShotUseCase

router = APIRouter(prefix="/api/shots", tags=["shots"])


@router.put("/{shot_id}", response_model=ShotOut)
def update_shot(shot_id: str, payload: ShotWriteRequest, repository=Depends(get_repository)) -> ShotOut:
    try:
        shot = UpdateShotUseCase(repository).execute(shot_id, ShotInput(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ShotOut.from_domain(shot)


@router.delete("/{shot_id}", status_code=204)
def delete_shot(shot_id: str, repository=Depends(get_repository)) -> Response:
    DeleteShotUseCase(repository).execute(shot_id)
    return Response(status_code=204)
