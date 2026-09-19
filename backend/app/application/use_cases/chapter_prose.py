"""Escritura de prosa completa por capitulo + derivacion de su hoja de
produccion (Paso 9.1/9.2 de SKILL.md) -- el hueco que la fase 1 dejo fuera
a proposito (ver README, "Fase 1"). La prosa manda: es el contenido
canonico de la historia; produccion.md es una adaptacion suya para el
formato motion comic, nunca al reves."""
from __future__ import annotations

import uuid

from app.adapters.outbound.storage.llm_json import extract_json
from app.application.ports.repository import ProjectRepositoryPort
from app.application.ports.text_generation import TextGenerationPort, TextGenerationRequest
from app.domain.shared.value_objects import ChapterStatus, ShotType
from app.domain.story.entities import Chapter, Shot
from app.prompts.production_sheet import build_production_sheet_prompt
from app.prompts.prose import build_prose_prompt

# "8-12 min de video necesita 1200-2500 palabras de prosa" (SKILL.md 9.1) --
# ~190 palabras por minuto objetivo, con piso/techo para capitulos muy
# cortos/largos donde esa proporcion dejaria de tener sentido.
_WORDS_PER_MINUTE = 190
_MIN_TARGET_WORDS = 600
_MAX_TARGET_WORDS = 4000


def _target_word_count(duracion_objetivo_min: int | None) -> int:
    minutos = duracion_objetivo_min or 10
    return max(_MIN_TARGET_WORDS, min(_MAX_TARGET_WORDS, round(minutos * _WORDS_PER_MINUTE)))


class WriteChapterProseUseCase:
    def __init__(self, repository: ProjectRepositoryPort, text_port: TextGenerationPort) -> None:
        self._repository = repository
        self._text_port = text_port

    async def execute(self, chapter_id: str) -> Chapter:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")
        canon = self._repository.get_canon(project.id)
        if canon is None:
            raise ValueError("Este proyecto todavia no tiene un canon generado -- generalo primero")
        episode = next((ep for ep in canon.temporada if ep.numero == chapter.numero), None)
        if episode is None:
            raise ValueError(
                f"El esqueleto de temporada del canon no tiene una fila para el capitulo {chapter.numero}"
            )

        characters = self._repository.list_characters(project.id)
        locations = self._repository.list_locations(project.id)
        target_words = _target_word_count(project.duracion_objetivo_min)

        system, user = build_prose_prompt(project, canon, episode, characters, locations, chapter.titulo, target_words)
        result = await self._text_port.generate(
            TextGenerationRequest(prompt=user, system=system, max_tokens=8000, temperature=0.85, json_mode=False)
        )

        prosa_path = project.root_path / f"capitulo-{chapter.numero}" / "capitulo.md"
        prosa_path.parent.mkdir(parents=True, exist_ok=True)
        prosa_path.write_text(result.text.strip() + "\n", encoding="utf-8")

        chapter.prosa_path = prosa_path
        self._repository.save_chapter(chapter)
        return chapter


class DeriveProductionSheetFromProseUseCase:
    def __init__(self, repository: ProjectRepositoryPort, text_port: TextGenerationPort) -> None:
        self._repository = repository
        self._text_port = text_port

    async def execute(self, chapter_id: str) -> list[Shot]:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {chapter_id}")
        if chapter.prosa_path is None or not chapter.prosa_path.exists():
            raise ValueError("Este capitulo todavia no tiene prosa escrita -- escribila primero")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")

        prosa = chapter.prosa_path.read_text(encoding="utf-8")
        characters = self._repository.list_characters(project.id)
        locations = self._repository.list_locations(project.id)
        character_slugs = {c.slug for c in characters}
        location_slugs = {l.slug for l in locations}

        system, user = build_production_sheet_prompt(project, prosa, characters, locations)
        result = await self._text_port.generate(
            TextGenerationRequest(prompt=user, system=system, max_tokens=8000, temperature=0.6, json_mode=True)
        )
        try:
            data = extract_json(result.text)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"El modelo no devolvio JSON valido para la hoja de produccion: {exc}\n\n"
                f"Respuesta cruda:\n{result.text[:2000]}"
            ) from exc

        shots: list[Shot] = []
        for i, raw in enumerate(data.get("shots", []), start=1):
            tipo = ShotType(raw.get("tipo")) if raw.get("tipo") in ("Narracion", "Dialogo") else ShotType.NARRACION
            personaje_ids = [pid for pid in raw.get("personaje_ids", []) if pid in character_slugs]
            escenario_id = raw.get("escenario_id")
            if escenario_id not in location_slugs:
                escenario_id = None
            shots.append(
                Shot(
                    id=str(uuid.uuid4()),
                    chapter_id=chapter_id,
                    orden=i,
                    tipo=tipo,
                    personaje_ids=personaje_ids,
                    escenario_id=escenario_id,
                    sub_escenario=raw.get("sub_escenario", "") or "",
                    momento_dia=raw.get("momento_dia", "") or "",
                    texto=raw.get("texto", "") or "",
                    prompt_imagen=raw.get("prompt_imagen", "") or "",
                    prompt_video=raw.get("prompt_video", "") or "",
                    movimiento_camara=raw.get("movimiento_camara", "") or "",
                    duracion_estimada_seg=float(raw["duracion_estimada_seg"]) if raw.get("duracion_estimada_seg") is not None else None,
                    sfx_musica=raw.get("sfx_musica", "") or "",
                )
            )

        if not shots:
            raise ValueError("El modelo no devolvio ninguna fila para la hoja de produccion")

        self._repository.replace_shots(chapter_id, shots)
        chapter.estado = ChapterStatus.HOJA_DERIVADA
        self._repository.save_chapter(chapter)
        return shots
