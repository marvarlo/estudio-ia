"""Exporta la hoja de produccion (fuente de verdad: la base de datos) de
vuelta a produccion.md -- para que la toolchain vieja del skill
historias-fantasia (build_prompts.py, etc.) siga funcionando sobre un
capitulo editado desde la web."""
from __future__ import annotations

from pathlib import Path

from app.adapters.outbound.storage.production_sheet_writer import write_production_sheet
from app.application.ports.repository import ProjectRepositoryPort


class ExportProductionSheetUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, chapter_id: str) -> Path:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")

        shots = self._repository.list_shots(chapter_id)
        output_path = chapter.produccion_path or (project.root_path / f"capitulo-{chapter.numero}" / "produccion.md")
        write_production_sheet(output_path, chapter, shots)

        if chapter.produccion_path is None:
            chapter.produccion_path = output_path
            self._repository.save_chapter(chapter)

        return output_path
