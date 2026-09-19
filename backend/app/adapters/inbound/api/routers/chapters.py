from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import get_repository
from app.adapters.inbound.api.schemas import ChapterShotsOut
from app.application.use_cases.project_queries import ListChapterShotsUseCase

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


@router.get("/{chapter_id}/shots", response_model=ChapterShotsOut)
def list_chapter_shots(chapter_id: str, repository=Depends(get_repository)) -> ChapterShotsOut:
    chapter, shots, assets = ListChapterShotsUseCase(repository).execute(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Capitulo no encontrado")
    return ChapterShotsOut.from_domain(chapter, shots, assets)
