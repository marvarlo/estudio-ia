"""Crear un capitulo vacio en un proyecto (para empezar a cargar su tabla de
produccion desde cero en la web, sin haber importado un produccion.md
existente)."""
from __future__ import annotations

import uuid

from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import ChapterStatus
from app.domain.story.entities import Chapter

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")


class CreateChapterUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, project_id: str, titulo: str, numero: int | None = None) -> Chapter:
        project = self._repository.get_project(project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {project_id}")
        existing = self._repository.list_chapters(project_id)
        resolved_numero = numero if numero is not None else (max((c.numero for c in existing), default=0) + 1)

        chapter_dir = project.root_path / f"capitulo-{resolved_numero}"
        chapter_dir.mkdir(parents=True, exist_ok=True)

        chapter = Chapter(
            id=str(uuid.uuid5(_NAMESPACE, f"chapter/{project_id}/{resolved_numero}")),
            project_id=project_id,
            numero=resolved_numero,
            titulo=titulo,
            produccion_path=chapter_dir / "produccion.md",
            estado=ChapterStatus.BORRADOR,
        )
        self._repository.save_chapter(chapter)
        return chapter
