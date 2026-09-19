from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response

from app.adapters.inbound.api.deps import (
    build_image_use_case,
    build_video_use_case,
    get_job_queue,
    get_media_probe,
    get_provider_registry,
    get_repository,
    resolve_adapter,
)
from app.adapters.inbound.api.schemas import (
    AssetOut,
    GenerateRequest,
    JobOut,
    SelectAssetRequest,
    ShotOut,
    ShotWriteRequest,
)
from app.application.ports.job_queue import JobQueuePort
from app.application.use_cases.asset_selection import ListShotAssetsUseCase, SelectShotAssetUseCase
from app.application.use_cases.generate_shot_audio import GenerateShotAudioUseCase
from app.application.use_cases.shot_editing import DeleteShotUseCase, ShotInput, UpdateShotUseCase
from app.config.cost_estimates import estimate_cost
from app.domain.jobs.entities import Job

router = APIRouter(prefix="/api/shots", tags=["shots"])


def _project_id_for_shot(repository, shot_id: str) -> str:
    shot = repository.get_shot(shot_id)
    if shot is None:
        raise HTTPException(status_code=404, detail=f"Shot no encontrado: {shot_id}")
    chapter = repository.get_chapter(shot.chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    return chapter.project_id


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


@router.post("/{shot_id}/image:generate", response_model=JobOut)
async def generate_shot_image(
    shot_id: str,
    payload: GenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    project_id = _project_id_for_shot(repository, shot_id)
    use_case = build_image_use_case(registry, repository, payload.provider_id)

    async def run() -> dict:
        asset = await use_case.execute(shot_id, select=payload.select)
        return {"asset_id": asset.id, "path": str(asset.path)}

    job = Job(
        id=str(uuid.uuid4()),
        project_id=project_id,
        shot_id=shot_id,
        kind="generate_shot_image",
        provider=payload.provider_id,
        cost_estimate=estimate_cost(payload.provider_id, "image"),
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)


@router.post("/{shot_id}/audio:generate", response_model=JobOut)
async def generate_shot_audio(
    shot_id: str,
    payload: GenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    project_id = _project_id_for_shot(repository, shot_id)
    tts_port = resolve_adapter(registry, payload.provider_id)
    use_case = GenerateShotAudioUseCase(repository, tts_port)

    async def run() -> dict:
        asset = await use_case.execute(shot_id, select=payload.select)
        return {"asset_id": asset.id, "path": str(asset.path)}

    job = Job(
        id=str(uuid.uuid4()),
        project_id=project_id,
        shot_id=shot_id,
        kind="generate_shot_audio",
        provider=payload.provider_id,
        cost_estimate=estimate_cost(payload.provider_id, "tts"),
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)


@router.post("/{shot_id}/video:generate", response_model=JobOut)
async def generate_shot_video(
    shot_id: str,
    payload: GenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    media_probe=Depends(get_media_probe),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    project_id = _project_id_for_shot(repository, shot_id)
    use_case = build_video_use_case(registry, repository, media_probe, payload.provider_id)

    async def run() -> dict:
        asset = await use_case.execute(shot_id, select=payload.select)
        return {"asset_id": asset.id, "path": str(asset.path)}

    job = Job(
        id=str(uuid.uuid4()),
        project_id=project_id,
        shot_id=shot_id,
        kind="generate_shot_video",
        provider=payload.provider_id,
        cost_estimate=estimate_cost(payload.provider_id, "video"),
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)


@router.get("/{shot_id}/assets", response_model=list[AssetOut])
def list_shot_assets(shot_id: str, repository=Depends(get_repository)) -> list[AssetOut]:
    assets = ListShotAssetsUseCase(repository).execute(shot_id)
    return [AssetOut.from_domain(a) for a in assets]


@router.post("/{shot_id}/assets:select", response_model=ShotOut)
def select_shot_asset(shot_id: str, payload: SelectAssetRequest, repository=Depends(get_repository)) -> ShotOut:
    try:
        shot = SelectShotAssetUseCase(repository).execute(shot_id, payload.asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ShotOut.from_domain(shot)
