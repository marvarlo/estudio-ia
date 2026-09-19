from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import (
    get_job_queue,
    get_media_probe,
    get_provider_registry,
    get_render_port,
    get_repository,
    get_settings,
    resolve_adapter,
)
from app.adapters.inbound.api.schemas import (
    CanonGenerateRequest,
    CanonOut,
    CastGenerateRequest,
    CastGenerationOut,
    ImportRequest,
    ImportSummaryOut,
    JobOut,
    ProjectCreateRequest,
    ProjectDetailOut,
    ProjectOut,
    VoiceOut,
)
from app.application.ports.job_queue import JobQueuePort
from app.application.use_cases.import_story_project import ImportStoryProjectUseCase
from app.application.use_cases.project_queries import GetProjectDetailUseCase, ListProjectsUseCase
from app.application.use_cases.render_season import RenderSeasonUseCase
from app.application.use_cases.story_generation import CreateStoryProjectUseCase, GenerateCanonUseCase, GenerateCastUseCase
from app.application.use_cases.voice_pool import AssignVoicesUseCase
from app.domain.jobs.entities import Job
from app.prompts.canon import StoryBrief
from app.prompts.cast import CastBrief

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(repository=Depends(get_repository)) -> list[ProjectOut]:
    projects = ListProjectsUseCase(repository).execute()
    return [ProjectOut.from_domain(p) for p in projects]


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreateRequest, repository=Depends(get_repository), settings=Depends(get_settings)
) -> ProjectOut:
    """Crea un proyecto NUEVO desde cero (paso 1 del wizard) -- distinto de
    /import, que trae uno ya producido con el skill original."""
    project = CreateStoryProjectUseCase(repository, settings.stories_root).execute(
        name=payload.name, estilo_visual=payload.estilo_visual, tono=payload.tono, plataformas=payload.plataformas
    )
    return ProjectOut.from_domain(project)


@router.post("/import", response_model=ImportSummaryOut)
def import_project(payload: ImportRequest, repository=Depends(get_repository)) -> ImportSummaryOut:
    """Importa (o reimporta) una carpeta de historia ya producida con el
    skill historias-fantasia. No copia archivos -- ver seccion 10 del doc de
    arquitectura."""
    try:
        summary = ImportStoryProjectUseCase(repository).execute(Path(payload.path))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ImportSummaryOut.from_domain(summary)


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project(project_id: str, repository=Depends(get_repository)) -> ProjectDetailOut:
    detail = GetProjectDetailUseCase(repository).execute(project_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return ProjectDetailOut.from_domain(detail)


@router.get("/{project_id}/canon", response_model=CanonOut)
def get_canon(project_id: str, repository=Depends(get_repository)) -> CanonOut:
    canon = repository.get_canon(project_id)
    if canon is None:
        raise HTTPException(status_code=404, detail="Este proyecto todavia no tiene un canon generado")
    return CanonOut.from_domain(canon)


@router.post("/{project_id}/canon:generate", response_model=CanonOut)
async def generate_canon(
    project_id: str,
    payload: CanonGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
) -> CanonOut:
    text_port = resolve_adapter(registry, payload.provider_id)
    brief = StoryBrief(
        estilo_narrativo=payload.estilo_narrativo,
        tono=payload.tono,
        plataformas=payload.plataformas,
        estilo_visual=payload.estilo_visual,
        num_episodios=payload.num_episodios,
        duracion_objetivo_min=payload.duracion_objetivo_min,
        semilla=payload.semilla,
    )
    try:
        canon = await GenerateCanonUseCase(repository, text_port).execute(project_id, brief)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CanonOut.from_domain(canon)


@router.post("/{project_id}/cast:generate", response_model=CastGenerationOut)
async def generate_cast(
    project_id: str,
    payload: CastGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
) -> CastGenerationOut:
    text_port = resolve_adapter(registry, payload.provider_id)
    brief = CastBrief(num_personajes=payload.num_personajes, num_escenarios=payload.num_escenarios, notas=payload.notas)
    try:
        result = await GenerateCastUseCase(repository, text_port).execute(project_id, brief)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CastGenerationOut.from_domain(result)


@router.post("/{project_id}/voices:assign", response_model=list[VoiceOut])
def assign_voices(project_id: str, repository=Depends(get_repository)) -> list[VoiceOut]:
    try:
        voices = AssignVoicesUseCase(repository).execute(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [VoiceOut.from_domain(v) for v in voices]


@router.post("/{project_id}/season:render", response_model=JobOut)
async def render_season(
    project_id: str,
    repository=Depends(get_repository),
    render_port=Depends(get_render_port),
    media_probe=Depends(get_media_probe),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    """Concatena todos los capitulos ya renderizados de la temporada con
    separadores y un cierre -- requiere que cada capitulo tenga ya un
    render seleccionado (fase 3). Puede tardar varios minutos."""
    project = repository.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    use_case = RenderSeasonUseCase(repository, render_port, media_probe)

    async def run() -> dict:
        asset = await use_case.execute(project_id)
        return {"asset_id": asset.id, "path": str(asset.path)}

    job = Job(id=str(uuid.uuid4()), project_id=project_id, kind="render_season", provider="remotion", cost_estimate=0.0)
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)
