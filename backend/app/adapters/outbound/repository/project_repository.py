"""Implementacion SQLite de ProjectRepositoryPort. Traduce entre dataclasses
del dominio (app.domain.story.entities) y filas SQLModel (models.py) -- este
es el UNICO archivo que conoce ambos lados."""
from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from app.adapters.outbound.repository.models import (
    AssetRow,
    CanonRow,
    ChapterRow,
    CharacterRow,
    JobRow,
    LocationRow,
    LyricLineRow,
    ProjectRow,
    ShotRow,
    TrackRow,
    VoicePoolVoiceRow,
    VoiceRow,
)
from app.domain.jobs.entities import Job
from app.domain.music.entities import LyricLine, LyricWord, Track
from app.domain.shared.value_objects import AssetKind, ChapterStatus, JobStatus, ProjectKind, ShotType, Tone
from app.domain.story.entities import (
    Asset,
    Canon,
    Chapter,
    Character,
    Location,
    Project,
    SeasonEpisode,
    Shot,
    Voice,
    VoicePoolVoice,
)


def _project_to_row(project: Project) -> ProjectRow:
    return ProjectRow(
        id=project.id,
        slug=project.slug,
        name=project.name,
        kind=project.kind.value,
        root_path=str(project.root_path),
        estilo_visual=project.estilo_visual,
        tono=project.tono.value,
        plataformas_json=json.dumps(project.plataformas, ensure_ascii=False),
        formatos_json=json.dumps(project.formatos, ensure_ascii=False),
        num_episodios=project.num_episodios,
        duracion_objetivo_min=project.duracion_objetivo_min,
        created_at=project.created_at,
        selected_season_asset_id=project.selected_season_asset_id,
    )


def _row_to_project(row: ProjectRow) -> Project:
    return Project(
        id=row.id,
        slug=row.slug,
        name=row.name,
        kind=ProjectKind(row.kind),
        root_path=Path(row.root_path),
        estilo_visual=row.estilo_visual,
        tono=Tone(row.tono),
        plataformas=json.loads(row.plataformas_json),
        formatos=json.loads(row.formatos_json),
        num_episodios=row.num_episodios,
        duracion_objetivo_min=row.duracion_objetivo_min,
        created_at=row.created_at,
        selected_season_asset_id=row.selected_season_asset_id,
    )


def _row_to_chapter(row: ChapterRow) -> Chapter:
    return Chapter(
        id=row.id,
        project_id=row.project_id,
        numero=row.numero,
        titulo=row.titulo,
        prosa_path=Path(row.prosa_path) if row.prosa_path else None,
        produccion_path=Path(row.produccion_path) if row.produccion_path else None,
        estado=ChapterStatus(row.estado),
        selected_render_asset_id=row.selected_render_asset_id,
    )


def _row_to_shot(row: ShotRow) -> Shot:
    tipo = ShotType(row.tipo) if row.tipo in ShotType._value2member_map_ else ShotType.NARRACION
    return Shot(
        id=row.id,
        chapter_id=row.chapter_id,
        orden=row.orden,
        tipo=tipo,
        personaje_ids=json.loads(row.personaje_ids_json),
        escenario_id=row.escenario_id,
        sub_escenario=row.sub_escenario,
        momento_dia=row.momento_dia,
        texto=row.texto,
        prompt_imagen=row.prompt_imagen,
        prompt_video=row.prompt_video,
        movimiento_camara=row.movimiento_camara,
        duracion_estimada_seg=row.duracion_estimada_seg,
        duracion_real_seg=row.duracion_real_seg,
        sfx_musica=row.sfx_musica,
        voice_id=row.voice_id,
        selected_image_asset_id=row.selected_image_asset_id,
        selected_audio_asset_id=row.selected_audio_asset_id,
        selected_video_asset_id=row.selected_video_asset_id,
    )


def _row_to_character(row: CharacterRow) -> Character:
    return Character(
        id=row.id,
        project_id=row.project_id,
        slug=row.slug,
        nombre=row.nombre,
        rol=row.rol,
        prompt_anchor=row.prompt_anchor,
        tokens_visuales=json.loads(row.tokens_visuales_json),
        voice_id=row.voice_id,
        reference_image_path=Path(row.reference_image_path) if row.reference_image_path else None,
    )


def _row_to_location(row: LocationRow) -> Location:
    return Location(
        id=row.id,
        project_id=row.project_id,
        slug=row.slug,
        nombre=row.nombre,
        descripcion_fija=row.descripcion_fija,
        reference_image_path=Path(row.reference_image_path) if row.reference_image_path else None,
    )


def _row_to_voice(row: VoiceRow) -> Voice:
    return Voice(
        id=row.id,
        project_id=row.project_id,
        personaje_id=row.personaje_id,
        proveedor=row.proveedor,
        voice_id_externo=row.voice_id_externo,
        modelo_tts=row.modelo_tts,
        notas_direccion=row.notas_direccion,
    )


def _row_to_voice_pool(row: VoicePoolVoiceRow) -> VoicePoolVoice:
    return VoicePoolVoice(
        id=row.id,
        proveedor=row.proveedor,
        voice_id_externo=row.voice_id_externo,
        nombre_interno=row.nombre_interno,
        modelo_tts=row.modelo_tts,
        atributos=json.loads(row.atributos_json),
        veces_usada=row.veces_usada,
        ultima_historia=row.ultima_historia,
    )


def _row_to_job(row: JobRow) -> Job:
    return Job(
        id=row.id,
        project_id=row.project_id,
        shot_id=row.shot_id,
        kind=row.kind,
        provider=row.provider,
        status=JobStatus(row.status),
        progress=row.progress,
        payload=json.loads(row.payload_json),
        result=json.loads(row.result_json) if row.result_json else None,
        error=row.error,
        cost_estimate=row.cost_estimate,
        cost_actual=row.cost_actual,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _row_to_track(row: TrackRow) -> Track:
    return Track(
        id=row.id,
        project_id=row.project_id,
        source_path=row.source_path,
        duration_seconds=row.duration_seconds,
        bpm=row.bpm,
        key=row.key,
        instrumental_path=row.instrumental_path,
    )


def _row_to_lyric_line(row: LyricLineRow) -> LyricLine:
    return LyricLine(
        id=row.id,
        track_id=row.track_id,
        index=row.index,
        text=row.text,
        start=row.start,
        end=row.end,
        words=[LyricWord(**w) for w in json.loads(row.words_json)],
    )


def _row_to_asset(row: AssetRow) -> Asset:
    return Asset(
        id=row.id,
        project_id=row.project_id,
        kind=AssetKind(row.kind),
        path=Path(row.path),
        chapter_id=row.chapter_id,
        shot_id=row.shot_id,
        width=row.width,
        height=row.height,
        provider=row.provider,
        model=row.model,
        created_at=row.created_at,
    )


class SqlProjectRepository:
    """Implementa ProjectRepositoryPort (application/ports/repository.py)
    contra SQLite via SQLModel. Una sesion por operacion, suficiente para
    el volumen de una app local; se revisa si se vuelve cuello de botella."""

    def __init__(self, engine) -> None:
        self._engine = engine

    # -- Project --------------------------------------------------------
    def save_project(self, project: Project) -> None:
        with Session(self._engine) as session:
            session.merge(_project_to_row(project))
            session.commit()

    def get_project(self, project_id: str) -> Project | None:
        with Session(self._engine) as session:
            row = session.get(ProjectRow, project_id)
            return _row_to_project(row) if row else None

    def get_project_by_slug(self, slug: str) -> Project | None:
        with Session(self._engine) as session:
            row = session.exec(select(ProjectRow).where(ProjectRow.slug == slug)).first()
            return _row_to_project(row) if row else None

    def list_projects(self) -> list[Project]:
        with Session(self._engine) as session:
            rows = session.exec(select(ProjectRow).order_by(ProjectRow.created_at.desc())).all()
            return [_row_to_project(row) for row in rows]

    # -- Canon ------------------------------------------------------------
    def save_canon(self, canon: Canon) -> None:
        with Session(self._engine) as session:
            session.merge(
                CanonRow(
                    project_id=canon.project_id,
                    logline=canon.logline,
                    premisa=canon.premisa,
                    reglas_sistema=canon.reglas_sistema,
                    glosario=canon.glosario,
                    temporada_json=json.dumps([ep.__dict__ for ep in canon.temporada], ensure_ascii=False),
                    raw_markdown=canon.raw_markdown,
                )
            )
            session.commit()

    def get_canon(self, project_id: str) -> Canon | None:
        with Session(self._engine) as session:
            row = session.get(CanonRow, project_id)
            if not row:
                return None
            return Canon(
                project_id=row.project_id,
                logline=row.logline,
                premisa=row.premisa,
                reglas_sistema=row.reglas_sistema,
                glosario=row.glosario,
                temporada=[SeasonEpisode(**ep) for ep in json.loads(row.temporada_json)],
                raw_markdown=row.raw_markdown,
            )

    # -- Chapter ------------------------------------------------------------
    def save_chapter(self, chapter: Chapter) -> None:
        with Session(self._engine) as session:
            session.merge(
                ChapterRow(
                    id=chapter.id,
                    project_id=chapter.project_id,
                    numero=chapter.numero,
                    titulo=chapter.titulo,
                    prosa_path=str(chapter.prosa_path) if chapter.prosa_path else None,
                    produccion_path=str(chapter.produccion_path) if chapter.produccion_path else None,
                    estado=chapter.estado.value,
                    selected_render_asset_id=chapter.selected_render_asset_id,
                )
            )
            session.commit()

    def list_chapters(self, project_id: str) -> list[Chapter]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(ChapterRow).where(ChapterRow.project_id == project_id).order_by(ChapterRow.numero)
            ).all()
            return [_row_to_chapter(row) for row in rows]

    def get_chapter(self, chapter_id: str) -> Chapter | None:
        with Session(self._engine) as session:
            row = session.get(ChapterRow, chapter_id)
            return _row_to_chapter(row) if row else None

    # -- Shot ---------------------------------------------------------------
    def replace_shots(self, chapter_id: str, shots: list[Shot]) -> None:
        with Session(self._engine) as session:
            existing = session.exec(select(ShotRow).where(ShotRow.chapter_id == chapter_id)).all()
            for row in existing:
                session.delete(row)
            for shot in shots:
                session.add(
                    ShotRow(
                        id=shot.id,
                        chapter_id=shot.chapter_id,
                        orden=shot.orden,
                        tipo=shot.tipo.value,
                        personaje_ids_json=json.dumps(shot.personaje_ids, ensure_ascii=False),
                        escenario_id=shot.escenario_id,
                        sub_escenario=shot.sub_escenario,
                        momento_dia=shot.momento_dia,
                        texto=shot.texto,
                        prompt_imagen=shot.prompt_imagen,
                        prompt_video=shot.prompt_video,
                        movimiento_camara=shot.movimiento_camara,
                        duracion_estimada_seg=shot.duracion_estimada_seg,
                        duracion_real_seg=shot.duracion_real_seg,
                        sfx_musica=shot.sfx_musica,
                        voice_id=shot.voice_id,
                        selected_image_asset_id=shot.selected_image_asset_id,
                        selected_audio_asset_id=shot.selected_audio_asset_id,
                        selected_video_asset_id=shot.selected_video_asset_id,
                    )
                )
            session.commit()

    def list_shots(self, chapter_id: str) -> list[Shot]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(ShotRow).where(ShotRow.chapter_id == chapter_id).order_by(ShotRow.orden)
            ).all()
            return [_row_to_shot(row) for row in rows]

    def get_shot(self, shot_id: str) -> Shot | None:
        with Session(self._engine) as session:
            row = session.get(ShotRow, shot_id)
            return _row_to_shot(row) if row else None

    def save_shot(self, shot: Shot) -> None:
        """Crea o actualiza UN shot puntual -- a diferencia de replace_shots
        (usado por el importador para reescribir el capitulo entero), esto
        es lo que usa la edicion en vivo de la tabla de produccion desde la
        web (seccion 5/11 del doc de arquitectura, 'la tabla se edita en la
        web')."""
        with Session(self._engine) as session:
            session.merge(
                ShotRow(
                    id=shot.id,
                    chapter_id=shot.chapter_id,
                    orden=shot.orden,
                    tipo=shot.tipo.value,
                    personaje_ids_json=json.dumps(shot.personaje_ids, ensure_ascii=False),
                    escenario_id=shot.escenario_id,
                    sub_escenario=shot.sub_escenario,
                    momento_dia=shot.momento_dia,
                    texto=shot.texto,
                    prompt_imagen=shot.prompt_imagen,
                    prompt_video=shot.prompt_video,
                    movimiento_camara=shot.movimiento_camara,
                    duracion_estimada_seg=shot.duracion_estimada_seg,
                    duracion_real_seg=shot.duracion_real_seg,
                    sfx_musica=shot.sfx_musica,
                    voice_id=shot.voice_id,
                    selected_image_asset_id=shot.selected_image_asset_id,
                    selected_audio_asset_id=shot.selected_audio_asset_id,
                    selected_video_asset_id=shot.selected_video_asset_id,
                )
            )
            session.commit()

    def delete_shot(self, shot_id: str) -> None:
        with Session(self._engine) as session:
            row = session.get(ShotRow, shot_id)
            if row:
                session.delete(row)
                session.commit()

    # -- Character / Location / Voice ---------------------------------------
    def save_character(self, character: Character) -> None:
        with Session(self._engine) as session:
            session.merge(
                CharacterRow(
                    id=character.id,
                    project_id=character.project_id,
                    slug=character.slug,
                    nombre=character.nombre,
                    rol=character.rol,
                    prompt_anchor=character.prompt_anchor,
                    tokens_visuales_json=json.dumps(character.tokens_visuales, ensure_ascii=False),
                    voice_id=character.voice_id,
                    reference_image_path=str(character.reference_image_path)
                    if character.reference_image_path
                    else None,
                )
            )
            session.commit()

    def list_characters(self, project_id: str) -> list[Character]:
        with Session(self._engine) as session:
            rows = session.exec(select(CharacterRow).where(CharacterRow.project_id == project_id)).all()
            return [_row_to_character(row) for row in rows]

    def get_character(self, character_id: str) -> Character | None:
        with Session(self._engine) as session:
            row = session.get(CharacterRow, character_id)
            return _row_to_character(row) if row else None

    def get_character_by_slug(self, project_id: str, slug: str) -> Character | None:
        with Session(self._engine) as session:
            row = session.exec(
                select(CharacterRow).where(CharacterRow.project_id == project_id, CharacterRow.slug == slug)
            ).first()
            return _row_to_character(row) if row else None

    def save_location(self, location: Location) -> None:
        with Session(self._engine) as session:
            session.merge(
                LocationRow(
                    id=location.id,
                    project_id=location.project_id,
                    slug=location.slug,
                    nombre=location.nombre,
                    descripcion_fija=location.descripcion_fija,
                    reference_image_path=str(location.reference_image_path)
                    if location.reference_image_path
                    else None,
                )
            )
            session.commit()

    def list_locations(self, project_id: str) -> list[Location]:
        with Session(self._engine) as session:
            rows = session.exec(select(LocationRow).where(LocationRow.project_id == project_id)).all()
            return [_row_to_location(row) for row in rows]

    def get_location(self, location_id: str) -> Location | None:
        with Session(self._engine) as session:
            row = session.get(LocationRow, location_id)
            return _row_to_location(row) if row else None

    def get_location_by_slug(self, project_id: str, slug: str) -> Location | None:
        with Session(self._engine) as session:
            row = session.exec(
                select(LocationRow).where(LocationRow.project_id == project_id, LocationRow.slug == slug)
            ).first()
            return _row_to_location(row) if row else None

    def save_voice(self, voice: Voice) -> None:
        with Session(self._engine) as session:
            session.merge(
                VoiceRow(
                    id=voice.id,
                    project_id=voice.project_id,
                    personaje_id=voice.personaje_id,
                    proveedor=voice.proveedor,
                    voice_id_externo=voice.voice_id_externo,
                    modelo_tts=voice.modelo_tts,
                    notas_direccion=voice.notas_direccion,
                )
            )
            session.commit()

    def list_voices(self, project_id: str) -> list[Voice]:
        with Session(self._engine) as session:
            rows = session.exec(select(VoiceRow).where(VoiceRow.project_id == project_id)).all()
            return [_row_to_voice(row) for row in rows]

    # -- Asset ----------------------------------------------------------
    def replace_scanned_assets(self, project_id: str, chapter_id: str, assets: list[Asset]) -> None:
        """Reemplaza los assets de origen filesystem (los que vinieron de
        escanear disco, no de un Job de generacion) de un capitulo, para que
        reimportar no duplique filas al volver a correr el importador sobre
        el mismo capitulo."""
        with Session(self._engine) as session:
            existing = session.exec(
                select(AssetRow).where(AssetRow.chapter_id == chapter_id, AssetRow.provider == "filesystem")
            ).all()
            for row in existing:
                session.delete(row)
            for asset in assets:
                session.add(
                    AssetRow(
                        id=asset.id,
                        project_id=project_id,
                        chapter_id=chapter_id,
                        shot_id=asset.shot_id,
                        kind=asset.kind.value,
                        path=str(asset.path),
                        width=asset.width,
                        height=asset.height,
                        provider=asset.provider,
                        model=asset.model,
                        created_at=asset.created_at,
                    )
                )
            session.commit()

    def save_asset(self, asset: Asset) -> None:
        """Un asset puntual (ficha de referencia generada, o cualquier otro
        generado por un Job) -- a diferencia de replace_scanned_assets, que
        es solo para el escaneo masivo del importador."""
        with Session(self._engine) as session:
            session.merge(
                AssetRow(
                    id=asset.id,
                    project_id=asset.project_id,
                    chapter_id=asset.chapter_id,
                    shot_id=asset.shot_id,
                    kind=asset.kind.value,
                    path=str(asset.path),
                    width=asset.width,
                    height=asset.height,
                    provider=asset.provider,
                    model=asset.model,
                    created_at=asset.created_at,
                )
            )
            session.commit()

    def get_asset(self, asset_id: str) -> Asset | None:
        with Session(self._engine) as session:
            row = session.get(AssetRow, asset_id)
            return _row_to_asset(row) if row else None

    def list_assets(self, project_id: str, chapter_id: str | None = None) -> list[Asset]:
        with Session(self._engine) as session:
            query = select(AssetRow).where(AssetRow.project_id == project_id)
            if chapter_id is not None:
                query = query.where(AssetRow.chapter_id == chapter_id)
            rows = session.exec(query).all()
            return [_row_to_asset(row) for row in rows]

    def list_assets_for_shot(self, shot_id: str) -> list[Asset]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(AssetRow).where(AssetRow.shot_id == shot_id).order_by(AssetRow.created_at.desc())
            ).all()
            return [_row_to_asset(row) for row in rows]

    # -- Pool de voces (nivel canal) ------------------------------------
    def save_pool_voice(self, voice: VoicePoolVoice) -> None:
        with Session(self._engine) as session:
            session.merge(
                VoicePoolVoiceRow(
                    id=voice.id,
                    proveedor=voice.proveedor,
                    voice_id_externo=voice.voice_id_externo,
                    nombre_interno=voice.nombre_interno,
                    modelo_tts=voice.modelo_tts,
                    atributos_json=json.dumps(voice.atributos, ensure_ascii=False),
                    veces_usada=voice.veces_usada,
                    ultima_historia=voice.ultima_historia,
                )
            )
            session.commit()

    def list_pool_voices(self) -> list[VoicePoolVoice]:
        with Session(self._engine) as session:
            rows = session.exec(select(VoicePoolVoiceRow)).all()
            return [_row_to_voice_pool(row) for row in rows]

    def get_pool_voice(self, voice_id: str) -> VoicePoolVoice | None:
        with Session(self._engine) as session:
            row = session.get(VoicePoolVoiceRow, voice_id)
            return _row_to_voice_pool(row) if row else None

    # -- Jobs -------------------------------------------------------------
    def save_job(self, job: Job) -> None:
        with Session(self._engine) as session:
            session.merge(
                JobRow(
                    id=job.id,
                    project_id=job.project_id,
                    shot_id=job.shot_id,
                    kind=job.kind,
                    provider=job.provider,
                    status=job.status.value,
                    progress=job.progress,
                    payload_json=json.dumps(job.payload, ensure_ascii=False),
                    result_json=json.dumps(job.result, ensure_ascii=False) if job.result is not None else None,
                    error=job.error,
                    cost_estimate=job.cost_estimate,
                    cost_actual=job.cost_actual,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
            )
            session.commit()

    def get_job(self, job_id: str) -> Job | None:
        with Session(self._engine) as session:
            row = session.get(JobRow, job_id)
            return _row_to_job(row) if row else None

    def list_jobs_by_shot(self, shot_id: str) -> list[Job]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(JobRow).where(JobRow.shot_id == shot_id).order_by(JobRow.created_at.desc())
            ).all()
            return [_row_to_job(row) for row in rows]

    # -- Musica (fase 4) --------------------------------------------------
    def save_track(self, track: Track) -> None:
        with Session(self._engine) as session:
            session.merge(
                TrackRow(
                    id=track.id,
                    project_id=track.project_id,
                    source_path=track.source_path,
                    duration_seconds=track.duration_seconds,
                    bpm=track.bpm,
                    key=track.key,
                    instrumental_path=track.instrumental_path,
                )
            )
            session.commit()

    def get_track(self, track_id: str) -> Track | None:
        with Session(self._engine) as session:
            row = session.get(TrackRow, track_id)
            return _row_to_track(row) if row else None

    def list_tracks(self, project_id: str) -> list[Track]:
        with Session(self._engine) as session:
            rows = session.exec(select(TrackRow).where(TrackRow.project_id == project_id)).all()
            return [_row_to_track(row) for row in rows]

    def replace_lyric_lines(self, track_id: str, lines: list[LyricLine]) -> None:
        with Session(self._engine) as session:
            existing = session.exec(select(LyricLineRow).where(LyricLineRow.track_id == track_id)).all()
            for row in existing:
                session.delete(row)
            for line in lines:
                session.add(
                    LyricLineRow(
                        id=line.id,
                        track_id=line.track_id,
                        index=line.index,
                        text=line.text,
                        start=line.start,
                        end=line.end,
                        words_json=json.dumps([w.__dict__ for w in line.words], ensure_ascii=False),
                    )
                )
            session.commit()

    def list_lyric_lines(self, track_id: str) -> list[LyricLine]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(LyricLineRow).where(LyricLineRow.track_id == track_id).order_by(LyricLineRow.index)
            ).all()
            return [_row_to_lyric_line(row) for row in rows]

    def get_lyric_line(self, line_id: str) -> LyricLine | None:
        with Session(self._engine) as session:
            row = session.get(LyricLineRow, line_id)
            return _row_to_lyric_line(row) if row else None

    def save_lyric_line(self, line: LyricLine) -> None:
        with Session(self._engine) as session:
            session.merge(
                LyricLineRow(
                    id=line.id,
                    track_id=line.track_id,
                    index=line.index,
                    text=line.text,
                    start=line.start,
                    end=line.end,
                    words_json=json.dumps([w.__dict__ for w in line.words], ensure_ascii=False),
                )
            )
            session.commit()

    def delete_lyric_line(self, line_id: str) -> None:
        with Session(self._engine) as session:
            row = session.get(LyricLineRow, line_id)
            if row:
                session.delete(row)
                session.commit()
