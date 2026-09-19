"""Casos de uso de escritura asistida por LLM: crear un proyecto nuevo desde
cero, generar su canon, y generar su cast (personajes + escenarios). Ver
seccion 11 del doc de arquitectura, fase 1 ("Contenido y cast")."""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.outbound.storage.canon_writer import render_canon_markdown
from app.adapters.outbound.storage.cast_writer import write_escenarios_json, write_personajes_json
from app.adapters.outbound.storage.llm_json import extract_json
from app.application.ports.repository import ProjectRepositoryPort
from app.application.ports.text_generation import TextGenerationPort, TextGenerationRequest
from app.domain.shared.value_objects import ProjectKind, Tone
from app.domain.story.entities import Canon, Character, Location, Project, SeasonEpisode
from app.prompts.canon import StoryBrief, build_canon_prompt
from app.prompts.cast import CastBrief, build_cast_prompt

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return _SLUG_RE.sub("-", normalized.lower()).strip("-") or "historia"


def _new_id(*parts: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "/".join(parts)))


class CreateStoryProjectUseCase:
    """Crea un proyecto NUEVO (no importado): escribe historia_config.json
    en `stories_root/{slug}/` y persiste el Project. El resto de los
    archivos (canon.md, personajes.json, etc.) los crean los casos de uso
    siguientes a medida que el usuario avanza en el wizard."""

    def __init__(self, repository: ProjectRepositoryPort, stories_root: Path) -> None:
        self._repository = repository
        self._stories_root = stories_root

    def execute(
        self,
        name: str,
        estilo_visual: str = "anime",
        tono: str = "NORMAL",
        plataformas: list[str] | None = None,
    ) -> Project:
        base_slug = _slugify(name)
        slug = base_slug
        suffix = 2
        while self._repository.get_project_by_slug(slug) is not None:
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        root_path = self._stories_root / slug
        root_path.mkdir(parents=True, exist_ok=True)

        project = Project(
            id=_new_id("project", slug),
            slug=slug,
            name=name,
            kind=ProjectKind.STORY,
            root_path=root_path,
            estilo_visual=estilo_visual,
            tono=Tone(tono) if tono in ("NORMAL", "SAFE") else Tone.NORMAL,
            plataformas=plataformas or ["YouTube"],
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_project(project)
        _write_historia_config(project)
        return project


def _write_historia_config(project: Project) -> None:
    import json

    payload = {
        "historia": project.slug,
        "estilo_visual": project.estilo_visual,
        "tono": project.tono.value,
        "plataformas": project.plataformas,
    }
    (project.root_path / "historia_config.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class GenerateCanonUseCase:
    def __init__(self, repository: ProjectRepositoryPort, text_port: TextGenerationPort) -> None:
        self._repository = repository
        self._text_port = text_port

    async def execute(self, project_id: str, brief: StoryBrief) -> Canon:
        project = self._repository.get_project(project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {project_id}")

        system, user = build_canon_prompt(brief)
        result = await self._text_port.generate(
            TextGenerationRequest(prompt=user, system=system, max_tokens=4000, temperature=0.9, json_mode=True)
        )
        try:
            data = extract_json(result.text)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"El modelo no devolvio JSON valido para el canon: {exc}\n\nRespuesta cruda:\n{result.text[:2000]}") from exc

        glosario_rows = data.get("glosario", []) or []
        glosario_md = "| Término | Significado | Notas de uso |\n|---|---|---|\n" + "\n".join(
            f"| {row.get('termino', '')} | {row.get('significado', '')} | {row.get('notas', '')} |"
            for row in glosario_rows
        )
        temporada = [
            SeasonEpisode(
                numero=int(ep.get("numero", idx + 1)),
                resumen=ep.get("resumen", ""),
                cliffhanger=ep.get("cliffhanger", ""),
            )
            for idx, ep in enumerate(data.get("temporada", []))
        ]

        canon = Canon(
            project_id=project_id,
            logline=data.get("logline", ""),
            premisa=data.get("premisa", ""),
            reglas_sistema=data.get("reglas_sistema", ""),
            glosario=glosario_md,
            temporada=temporada,
        )

        # El brief manda sobre los parametros de produccion del proyecto --
        # se persisten aca porque es el primer punto del wizard donde el
        # usuario los confirma todos juntos.
        project.tono = Tone(brief.tono) if brief.tono in ("NORMAL", "SAFE") else project.tono
        project.plataformas = brief.plataformas or project.plataformas
        project.estilo_visual = brief.estilo_visual or project.estilo_visual
        project.num_episodios = brief.num_episodios
        project.duracion_objetivo_min = brief.duracion_objetivo_min
        self._repository.save_project(project)

        canon.raw_markdown = render_canon_markdown(project, canon)
        (project.root_path / "canon.md").write_text(canon.raw_markdown, encoding="utf-8")
        self._repository.save_canon(canon)
        return canon


@dataclass
class CastGenerationResult:
    characters: list[Character] = field(default_factory=list)
    locations: list[Location] = field(default_factory=list)


class GenerateCastUseCase:
    def __init__(self, repository: ProjectRepositoryPort, text_port: TextGenerationPort) -> None:
        self._repository = repository
        self._text_port = text_port

    async def execute(self, project_id: str, brief: CastBrief) -> CastGenerationResult:
        project = self._repository.get_project(project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {project_id}")
        canon = self._repository.get_canon(project_id)
        if canon is None:
            raise ValueError("Este proyecto todavia no tiene un canon generado -- generalo primero")

        system, user = build_cast_prompt(project, canon, brief)
        result = await self._text_port.generate(
            TextGenerationRequest(prompt=user, system=system, max_tokens=6000, temperature=0.9, json_mode=True)
        )
        try:
            data = extract_json(result.text)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"El modelo no devolvio JSON valido para el cast: {exc}\n\nRespuesta cruda:\n{result.text[:2000]}") from exc

        characters: list[Character] = []
        for raw in data.get("personajes", []):
            slug = raw.get("id") or _slugify(raw.get("nombre", "personaje"))
            tokens = {
                "descripcion_corta": raw.get("descripcion_corta", ""),
                "cabello": raw.get("cabello", ""),
                "ojos": raw.get("ojos", ""),
                "marca_distintiva": raw.get("marca_distintiva", ""),
                "atuendo_base": raw.get("atuendo_base", ""),
                "prompt_anchor": raw.get("prompt_anchor", ""),
            }
            character = Character(
                id=_new_id("character", project_id, slug),
                project_id=project_id,
                slug=slug,
                nombre=raw.get("nombre", slug),
                rol=raw.get("rol", ""),
                prompt_anchor=tokens["prompt_anchor"],
                tokens_visuales=tokens,
            )
            self._repository.save_character(character)
            characters.append(character)

        locations: list[Location] = []
        for raw in data.get("escenarios", []):
            slug = raw.get("id") or _slugify(raw.get("nombre", "escenario"))
            location = Location(
                id=_new_id("location", project_id, slug),
                project_id=project_id,
                slug=slug,
                nombre=raw.get("nombre", slug),
                descripcion_fija=raw.get("descripcion_fija", ""),
            )
            self._repository.save_location(location)
            locations.append(location)

        write_personajes_json(project.root_path, project.slug, characters)
        write_escenarios_json(project.root_path, project.slug, locations)
        return CastGenerationResult(characters=characters, locations=locations)
