from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import (
    build_image_use_case,
    build_render_use_case,
    get_job_queue,
    get_media_probe,
    get_provider_registry,
    get_render_port,
    get_repository,
    resolve_adapter,
)
from app.adapters.inbound.api.schemas import (
    BatchGenerateOut,
    BatchGenerateRequest,
    ChapterCreateRequest,
    ChapterOut,
    ChapterShotsOut,
    ExportOut,
    JobOut,
    LintWarningOut,
    ProductionSheetDeriveRequest,
    ProseGenerateRequest,
    ProseOut,
    ProseUpdateRequest,
    ReorderShotsRequest,
    ShotOut,
    ShotWriteRequest,
)
from app.application.ports.job_queue import JobQueuePort
from app.application.ports.media_probe import MediaProbePort
from app.application.ports.render import RenderPort
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.chapter_prose import DeriveProductionSheetFromProseUseCase, WriteChapterProseUseCase
from app.application.use_cases.export_production_sheet import ExportProductionSheetUseCase
from app.application.use_cases.generate_shot_audio import GenerateShotAudioUseCase
from app.application.use_cases.lint import LintProductionSheetUseCase
from app.application.use_cases.project_queries import ListChapterShotsUseCase
from app.application.use_cases.shot_editing import CreateShotUseCase, ReorderShotsUseCase, ShotInput
from app.config.cost_estimates import estimate_cost
from app.domain.jobs.entities import Job

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


def _to_shot_input(payload: ShotWriteRequest) -> ShotInput:
    return ShotInput(**payload.model_dump())


@router.post("", response_model=ChapterOut)
def create_chapter(payload: ChapterCreateRequest, repository=Depends(get_repository)) -> ChapterOut:
    try:
        chapter = CreateChapterUseCase(repository).execute(payload.project_id, payload.titulo, payload.numero)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ChapterOut.from_domain(chapter)


@router.get("/{chapter_id}/shots", response_model=ChapterShotsOut)
def list_chapter_shots(chapter_id: str, repository=Depends(get_repository)) -> ChapterShotsOut:
    chapter, shots, assets = ListChapterShotsUseCase(repository).execute(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    return ChapterShotsOut.from_domain(chapter, shots, assets)


@router.post("/{chapter_id}/shots", response_model=ShotOut)
def create_shot(chapter_id: str, payload: ShotWriteRequest, repository=Depends(get_repository)) -> ShotOut:
    shot = CreateShotUseCase(repository).execute(chapter_id, _to_shot_input(payload))
    return ShotOut.from_domain(shot)


@router.post("/{chapter_id}/shots:reorder", response_model=list[ShotOut])
def reorder_shots(chapter_id: str, payload: ReorderShotsRequest, repository=Depends(get_repository)) -> list[ShotOut]:
    try:
        shots = ReorderShotsUseCase(repository).execute(chapter_id, payload.ordered_shot_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [ShotOut.from_domain(s) for s in shots]


@router.get("/{chapter_id}/lint", response_model=list[LintWarningOut])
def lint_chapter(chapter_id: str, repository=Depends(get_repository)) -> list[LintWarningOut]:
    try:
        warnings = LintProductionSheetUseCase(repository).execute(chapter_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [LintWarningOut.from_domain(w) for w in warnings]


@router.post("/{chapter_id}/export", response_model=ExportOut)
def export_chapter(chapter_id: str, repository=Depends(get_repository)) -> ExportOut:
    try:
        path = ExportProductionSheetUseCase(repository).execute(chapter_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExportOut(path=str(path))


@router.post("/{chapter_id}/images:generate", response_model=BatchGenerateOut)
async def generate_chapter_images(
    chapter_id: str,
    payload: BatchGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    queue: JobQueuePort = Depends(get_job_queue),
) -> BatchGenerateOut:
    """Encola un job de imagen por cada shot del capitulo que todavia no
    tiene una imagen seleccionada (o TODOS si force=True) -- confirmar el
    tamano del lote antes de llamar esto queda del lado del frontend
    (seccion 9 del doc de arquitectura, 'mostrar costo estimado')."""
    chapter = repository.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    use_case = build_image_use_case(registry, repository, payload.provider_id)
    shots = repository.list_shots(chapter_id)

    jobs: list[JobOut] = []
    skipped = 0
    for shot in shots:
        if shot.selected_image_asset_id and not payload.force:
            skipped += 1
            continue

        async def run(shot_id: str = shot.id) -> dict:
            asset = await use_case.execute(shot_id, select=payload.select)
            return {"asset_id": asset.id, "path": str(asset.path)}

        job = Job(
            id=str(uuid.uuid4()),
            project_id=chapter.project_id,
            shot_id=shot.id,
            kind="generate_shot_image",
            provider=payload.provider_id,
            cost_estimate=estimate_cost(payload.provider_id, "image"),
        )
        job = await queue.enqueue(job, run)
        jobs.append(JobOut.from_domain(job))

    return BatchGenerateOut(jobs=jobs, skipped=skipped)


@router.get("/{chapter_id}/prose", response_model=ProseOut)
def get_prose(chapter_id: str, repository=Depends(get_repository)) -> ProseOut:
    chapter = repository.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    if chapter.prosa_path is None or not chapter.prosa_path.exists():
        return ProseOut(text="", path=None)
    return ProseOut(text=chapter.prosa_path.read_text(encoding="utf-8"), path=str(chapter.prosa_path))


@router.put("/{chapter_id}/prose", response_model=ProseOut)
def update_prose(chapter_id: str, payload: ProseUpdateRequest, repository=Depends(get_repository)) -> ProseOut:
    """Permite corregir la prosa a mano antes de derivar la hoja de
    produccion -- corregir tono/ritmo en texto es mucho mas barato que
    descubrir el mismo problema despues de generar imagenes/audio (SKILL.md
    9.1)."""
    chapter = repository.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    project = repository.get_project(chapter.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    prosa_path = chapter.prosa_path or (project.root_path / f"capitulo-{chapter.numero}" / "capitulo.md")
    prosa_path.parent.mkdir(parents=True, exist_ok=True)
    prosa_path.write_text(payload.text, encoding="utf-8")
    if chapter.prosa_path is None:
        chapter.prosa_path = prosa_path
        repository.save_chapter(chapter)
    return ProseOut(text=payload.text, path=str(prosa_path))


@router.post("/{chapter_id}/prose:generate", response_model=JobOut)
async def generate_prose(
    chapter_id: str,
    payload: ProseGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    chapter = repository.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    text_port = resolve_adapter(registry, payload.provider_id)
    use_case = WriteChapterProseUseCase(repository, text_port)

    async def run() -> dict:
        updated = await use_case.execute(chapter_id)
        text = updated.prosa_path.read_text(encoding="utf-8") if updated.prosa_path else ""
        return {"prosa_path": str(updated.prosa_path), "word_count": len(text.split())}

    job = Job(
        id=str(uuid.uuid4()), project_id=chapter.project_id, kind="write_chapter_prose",
        provider=payload.provider_id, cost_estimate=estimate_cost(payload.provider_id, "text"),
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)


@router.post("/{chapter_id}/production-sheet:derive", response_model=JobOut)
async def derive_production_sheet(
    chapter_id: str,
    payload: ProductionSheetDeriveRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    chapter = repository.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    text_port = resolve_adapter(registry, payload.provider_id)
    use_case = DeriveProductionSheetFromProseUseCase(repository, text_port)

    async def run() -> dict:
        shots = await use_case.execute(chapter_id)
        return {"shots_count": len(shots)}

    job = Job(
        id=str(uuid.uuid4()), project_id=chapter.project_id, kind="derive_production_sheet",
        provider=payload.provider_id, cost_estimate=estimate_cost(payload.provider_id, "text"),
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)


@router.post("/{chapter_id}/render:generate", response_model=JobOut)
async def render_chapter(
    chapter_id: str,
    repository=Depends(get_repository),
    render_port: RenderPort = Depends(get_render_port),
    media_probe: MediaProbePort = Depends(get_media_probe),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    """Encola el render final del capitulo (sidecar Remotion, fase 3): pausa
    hasta que el proceso de Node termine, asi que siempre va por Job -- un
    capitulo de varios minutos tarda bastante mas que una generacion de
    imagen/audio puntual."""
    chapter = repository.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    use_case = build_render_use_case(repository, render_port, media_probe)

    async def run() -> dict:
        asset = await use_case.execute(chapter_id)
        return {"asset_id": asset.id, "path": str(asset.path)}

    job = Job(
        id=str(uuid.uuid4()),
        project_id=chapter.project_id,
        kind="render_chapter",
        provider="remotion",
        payload={"chapter_id": chapter_id},
        cost_estimate=0.0,
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)


@router.post("/{chapter_id}/audio:generate", response_model=BatchGenerateOut)
async def generate_chapter_audio(
    chapter_id: str,
    payload: BatchGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    queue: JobQueuePort = Depends(get_job_queue),
) -> BatchGenerateOut:
    chapter = repository.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    tts_port = resolve_adapter(registry, payload.provider_id)
    use_case = GenerateShotAudioUseCase(repository, tts_port)
    shots = repository.list_shots(chapter_id)

    jobs: list[JobOut] = []
    skipped = 0
    for shot in shots:
        if shot.selected_audio_asset_id and not payload.force:
            skipped += 1
            continue

        async def run(shot_id: str = shot.id) -> dict:
            asset = await use_case.execute(shot_id, select=payload.select)
            return {"asset_id": asset.id, "path": str(asset.path)}

        job = Job(
            id=str(uuid.uuid4()),
            project_id=chapter.project_id,
            shot_id=shot.id,
            kind="generate_shot_audio",
            provider=payload.provider_id,
            cost_estimate=estimate_cost(payload.provider_id, "tts"),
        )
        job = await queue.enqueue(job, run)
        jobs.append(JobOut.from_domain(job))

    return BatchGenerateOut(jobs=jobs, skipped=skipped)
