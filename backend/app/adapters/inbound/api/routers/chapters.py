from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import get_repository
from app.adapters.inbound.api.schemas import (
    ChapterCreateRequest,
    ChapterOut,
    ChapterShotsOut,
    ExportOut,
    LintWarningOut,
    ReorderShotsRequest,
    ShotOut,
    ShotWriteRequest,
)
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.export_production_sheet import ExportProductionSheetUseCase
from app.application.use_cases.lint import LintProductionSheetUseCase
from app.application.use_cases.project_queries import ListChapterShotsUseCase
from app.application.use_cases.shot_editing import (
    CreateShotUseCase,
    DeleteShotUseCase,
    ReorderShotsUseCase,
    ShotInput,
    UpdateShotUseCase,
)

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
