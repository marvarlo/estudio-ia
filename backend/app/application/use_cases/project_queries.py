"""Casos de uso de solo lectura para proyectos/capitulos/shots/cast.

Se agrupan en un archivo porque son consultas triviales sobre el repositorio
-- separarlas en un archivo por clase no aportaria nada en esta fase. Si
alguna gana logica propia (permisos, filtros complejos), se le da su propio
archivo en ese momento.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.repository import ProjectRepositoryPort
from app.domain.story.entities import Asset, Canon, Chapter, Character, Location, Project, Shot, Voice


@dataclass
class ProjectDetail:
    project: Project
    canon: Canon | None
    chapters: list[Chapter]
    characters: list[Character]
    locations: list[Location]
    voices: list[Voice]


class ListProjectsUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self) -> list[Project]:
        return self._repository.list_projects()


class GetProjectDetailUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, project_id: str) -> ProjectDetail | None:
        project = self._repository.get_project(project_id)
        if project is None:
            return None
        return ProjectDetail(
            project=project,
            canon=self._repository.get_canon(project_id),
            chapters=self._repository.list_chapters(project_id),
            characters=self._repository.list_characters(project_id),
            locations=self._repository.list_locations(project_id),
            voices=self._repository.list_voices(project_id),
        )


class ListChapterShotsUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, chapter_id: str) -> tuple[Chapter | None, list[Shot], list[Asset]]:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            return None, [], []
        shots = self._repository.list_shots(chapter_id)
        assets = self._repository.list_assets(chapter.project_id, chapter_id=chapter_id)
        return chapter, shots, assets
