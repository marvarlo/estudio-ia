"""Caso de uso: ImportStoryProject.

Escanea una carpeta de historia ya producida con el skill historias-fantasia
(historia_config.json, canon.md, personajes.json, escenarios.json, voces.json,
capitulo-N/produccion.md + sus assets) y la persiste en la base de datos de
Estudio IA, sin copiar ni mover ningun archivo. Reimportar la misma carpeta
es idempotente: actualiza en vez de duplicar, porque los ids se derivan de
forma deterministica del slug y del numero de capitulo/fila.

Ver seccion 10 del doc de arquitectura ("Importacion").
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.adapters.outbound.storage.asset_scanner import scan_chapter_assets
from app.adapters.outbound.storage.production_sheet_parser import parse_production_sheet_file
from app.adapters.outbound.storage.story_folder_reader import (
    discover_chapter_numbers,
    read_canon,
    read_chapter_title,
    read_historia_config,
    read_json_optional,
)
from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import AssetKind, ChapterStatus, ProjectKind, ShotType, Tone
from app.domain.story.entities import Asset, Canon, Chapter, Character, Location, Project, Shot, Voice

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")


def _deterministic_id(*parts: str) -> str:
    """uuid5 (no uuid4 al azar): reimportar la misma carpeta produce el
    MISMO id para la misma entidad, asi replace_shots/replace_scanned_assets
    actualizan en vez de duplicar filas en cada reimportacion."""
    return str(uuid.uuid5(_NAMESPACE, "/".join(parts)))


@dataclass
class ImportSummary:
    project_id: str
    slug: str
    name: str
    chapters_imported: int
    shots_imported: int
    characters_imported: int
    locations_imported: int
    voices_imported: int
    assets_found: int
    warnings: list[str] = field(default_factory=list)


class ImportStoryProjectUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, root_path: Path) -> ImportSummary:
        root_path = root_path.resolve()
        if not root_path.exists():
            raise FileNotFoundError(f"No existe la carpeta de historia: {root_path}")

        warnings: list[str] = []
        config = read_historia_config(root_path)
        slug = config.get("historia") or root_path.name
        project_id = _deterministic_id("project", slug)

        canon_summary = read_canon(root_path, fallback_title=slug)
        tono_raw = config.get("tono", "NORMAL")
        tono = Tone(tono_raw) if tono_raw in ("NORMAL", "SAFE") else Tone.NORMAL

        project = Project(
            id=project_id,
            slug=slug,
            name=canon_summary.title,
            kind=ProjectKind.STORY,
            root_path=root_path,
            estilo_visual=config.get("estilo_visual", "anime"),
            tono=tono,
            plataformas=config.get("plataformas", []),
            formatos=[],
        )
        self._repository.save_project(project)
        self._repository.save_canon(
            Canon(project_id=project_id, logline=canon_summary.logline, raw_markdown=canon_summary.raw_markdown)
        )

        characters_imported = self._import_characters(project_id, root_path, warnings)
        locations_imported = self._import_locations(project_id, root_path, warnings)
        voices_imported = self._import_voices(project_id, root_path, warnings)

        chapter_numbers = discover_chapter_numbers(root_path)
        total_shots = 0
        total_assets = 0
        formatos_encontrados: set[str] = set()

        for numero in chapter_numbers:
            chapter_dir = root_path / f"capitulo-{numero}"
            produccion_path = chapter_dir / "produccion.md"
            prosa_path = chapter_dir / "capitulo.md"
            chapter_id = _deterministic_id("chapter", project_id, str(numero))
            titulo = read_chapter_title(produccion_path, numero)

            parsed_rows = parse_production_sheet_file(produccion_path)
            shots = [
                Shot(
                    id=_deterministic_id("shot", chapter_id, str(row.orden)),
                    chapter_id=chapter_id,
                    orden=row.orden,
                    tipo=ShotType(row.tipo) if row.tipo in ("Narracion", "Dialogo") else ShotType.NARRACION,
                    personaje_ids=row.personaje_ids,
                    escenario_id=row.escenario_id,
                    sub_escenario=row.sub_escenario,
                    momento_dia=row.momento_dia,
                    texto=row.texto,
                    prompt_imagen=row.prompt_imagen,
                    prompt_video=row.prompt_video,
                    movimiento_camara=row.movimiento_camara,
                    duracion_estimada_seg=row.duracion_estimada_seg,
                    sfx_musica=row.sfx_musica,
                )
                for row in parsed_rows
            ]
            shots_by_orden = {shot.orden: shot for shot in shots}

            scanned_assets = scan_chapter_assets(chapter_dir)
            assets: list[Asset] = []
            for scanned in scanned_assets:
                shot_id = None
                if scanned.shot_orden is not None and scanned.shot_orden in shots_by_orden:
                    shot_id = shots_by_orden[scanned.shot_orden].id
                assets.append(
                    Asset(
                        id=_deterministic_id("asset", chapter_id, scanned.kind.value, str(scanned.path)),
                        project_id=project_id,
                        chapter_id=chapter_id,
                        shot_id=shot_id,
                        kind=scanned.kind,
                        path=scanned.path,
                        width=scanned.width,
                        height=scanned.height,
                        provider="filesystem",
                    )
                )
                if scanned.width and scanned.height:
                    formatos_encontrados.add(f"{scanned.width}x{scanned.height}")

            estado = ChapterStatus.BORRADOR
            if shots:
                estado = ChapterStatus.HOJA_DERIVADA
            if any(a.kind == AssetKind.IMAGE for a in assets):
                estado = ChapterStatus.ASSETS

            chapter = Chapter(
                id=chapter_id,
                project_id=project_id,
                numero=numero,
                titulo=titulo,
                prosa_path=prosa_path if prosa_path.exists() else None,
                produccion_path=produccion_path,
                estado=estado,
            )
            self._repository.save_chapter(chapter)
            self._repository.replace_shots(chapter_id, shots)
            self._repository.replace_scanned_assets(project_id, chapter_id, assets)

            if not shots:
                warnings.append(f"Capitulo {numero}: produccion.md sin filas reconocidas")

            total_shots += len(shots)
            total_assets += len(assets)

        if formatos_encontrados:
            project.formatos = sorted(formatos_encontrados)
            self._repository.save_project(project)

        if not chapter_numbers:
            warnings.append("No se encontraron capitulos (carpetas capitulo-N con produccion.md)")

        return ImportSummary(
            project_id=project_id,
            slug=slug,
            name=project.name,
            chapters_imported=len(chapter_numbers),
            shots_imported=total_shots,
            characters_imported=characters_imported,
            locations_imported=locations_imported,
            voices_imported=voices_imported,
            assets_found=total_assets,
            warnings=warnings,
        )

    def _import_characters(self, project_id: str, root_path: Path, warnings: list[str]) -> int:
        data = read_json_optional(root_path / "personajes.json")
        if not data:
            warnings.append("personajes.json no encontrado")
            return 0
        count = 0
        for raw in data.get("personajes", []):
            personaje_id = raw.get("id")
            if not personaje_id:
                continue
            tokens = raw.get("tokens_visuales_fijos", {}) or {}
            ref = raw.get("referencia_imagen", {}) or {}
            ref_path_str = ref.get("ruta_imagen_referencia") or ""
            character = Character(
                id=_deterministic_id("character", project_id, personaje_id),
                project_id=project_id,
                slug=personaje_id,
                nombre=raw.get("nombre", personaje_id),
                rol=raw.get("rol", ""),
                prompt_anchor=tokens.get("prompt_anchor", ""),
                tokens_visuales=tokens,
                reference_image_path=(root_path / ref_path_str) if ref_path_str else None,
            )
            self._repository.save_character(character)
            count += 1
        return count

    def _import_locations(self, project_id: str, root_path: Path, warnings: list[str]) -> int:
        data = read_json_optional(root_path / "escenarios.json")
        if not data:
            warnings.append("escenarios.json no encontrado")
            return 0
        count = 0
        for raw in data.get("escenarios", []):
            escenario_id = raw.get("id")
            if not escenario_id:
                continue
            ref = raw.get("referencia_imagen", {}) or {}
            ref_path_str = ref.get("ruta_imagen_referencia") or ""
            location = Location(
                id=_deterministic_id("location", project_id, escenario_id),
                project_id=project_id,
                slug=escenario_id,
                nombre=raw.get("nombre", escenario_id),
                descripcion_fija=raw.get("descripcion_fija", ""),
                reference_image_path=(root_path / ref_path_str) if ref_path_str else None,
            )
            self._repository.save_location(location)
            count += 1
        return count

    def _import_voices(self, project_id: str, root_path: Path, warnings: list[str]) -> int:
        data = read_json_optional(root_path / "voces.json")
        if not data:
            warnings.append("voces.json no encontrado")
            return 0
        count = 0
        narrador = data.get("narrador", {}) or {}
        if narrador.get("voz_id_referencia"):
            voice = Voice(
                id=_deterministic_id("voice", project_id, "narrador"),
                project_id=project_id,
                personaje_id=None,
                proveedor="ElevenLabs",
                voice_id_externo=narrador["voz_id_referencia"],
                notas_direccion="Narrador",
            )
            self._repository.save_voice(voice)
            count += 1
        for raw in data.get("reparto", []):
            personaje_id = raw.get("personaje_id")
            voice_externo = raw.get("voz_id_asignada")
            if not personaje_id or not voice_externo:
                continue
            voice = Voice(
                id=_deterministic_id("voice", project_id, personaje_id),
                project_id=project_id,
                personaje_id=personaje_id,
                proveedor="ElevenLabs",
                voice_id_externo=voice_externo,
                notas_direccion=raw.get("notas_direccion_especificas", ""),
            )
            self._repository.save_voice(voice)
            count += 1
        return count
