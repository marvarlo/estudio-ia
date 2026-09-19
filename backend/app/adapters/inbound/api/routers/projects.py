from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import get_repository
from app.adapters.inbound.api.schemas import ImportRequest, ImportSummaryOut, ProjectDetailOut, ProjectOut
from app.application.use_cases.import_story_project import ImportStoryProjectUseCase
from app.application.use_cases.project_queries import GetProjectDetailUseCase, ListProjectsUseCase

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(repository=Depends(get_repository)) -> list[ProjectOut]:
    projects = ListProjectsUseCase(repository).execute()
    return [ProjectOut.from_domain(p) for p in projects]


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
