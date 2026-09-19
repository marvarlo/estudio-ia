"""Tablas SQLModel. Los campos lista/dict del dominio (plataformas,
personaje_ids, tokens_visuales) se guardan como TEXT con JSON adentro y se
(de)serializan en project_repository.py -- el dominio nunca ve una columna
SQL, solo listas y dicts de Python.
"""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class ProjectRow(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    kind: str
    root_path: str
    estilo_visual: str = "anime"
    tono: str = "NORMAL"
    plataformas_json: str = "[]"
    formatos_json: str = "[]"
    num_episodios: int | None = None
    duracion_objetivo_min: int | None = None
    created_at: datetime | None = None
    selected_season_asset_id: str | None = None


class CanonRow(SQLModel, table=True):
    __tablename__ = "canons"

    project_id: str = Field(primary_key=True, foreign_key="projects.id")
    logline: str = ""
    premisa: str = ""
    reglas_sistema: str = ""
    glosario: str = ""
    temporada_json: str = "[]"
    raw_markdown: str = ""


class ChapterRow(SQLModel, table=True):
    __tablename__ = "chapters"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True, foreign_key="projects.id")
    numero: int
    titulo: str
    prosa_path: str | None = None
    produccion_path: str | None = None
    estado: str = "borrador"
    selected_render_asset_id: str | None = None


class ShotRow(SQLModel, table=True):
    __tablename__ = "shots"

    id: str = Field(primary_key=True)
    chapter_id: str = Field(index=True, foreign_key="chapters.id")
    orden: int
    tipo: str
    personaje_ids_json: str = "[]"
    escenario_id: str | None = None
    sub_escenario: str = ""
    momento_dia: str = ""
    texto: str = ""
    prompt_imagen: str = ""
    prompt_video: str = ""
    movimiento_camara: str = ""
    duracion_estimada_seg: float | None = None
    duracion_real_seg: float | None = None
    sfx_musica: str = ""
    voice_id: str | None = None
    start_seg: float | None = None
    selected_image_asset_id: str | None = None
    selected_audio_asset_id: str | None = None
    selected_video_asset_id: str | None = None


class CharacterRow(SQLModel, table=True):
    __tablename__ = "characters"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True, foreign_key="projects.id")
    slug: str = Field(default="", index=True)
    nombre: str
    rol: str = ""
    prompt_anchor: str = ""
    tokens_visuales_json: str = "{}"
    voice_id: str | None = None
    reference_image_path: str | None = None


class LocationRow(SQLModel, table=True):
    __tablename__ = "locations"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True, foreign_key="projects.id")
    slug: str = Field(default="", index=True)
    nombre: str
    descripcion_fija: str = ""
    reference_image_path: str | None = None


class VoiceRow(SQLModel, table=True):
    __tablename__ = "voices"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True, foreign_key="projects.id")
    personaje_id: str | None = None
    proveedor: str = ""
    voice_id_externo: str = ""
    modelo_tts: str = ""
    notas_direccion: str = ""


class AssetRow(SQLModel, table=True):
    __tablename__ = "assets"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True, foreign_key="projects.id")
    chapter_id: str | None = Field(default=None, index=True)
    shot_id: str | None = Field(default=None, index=True)
    kind: str
    path: str
    width: int | None = None
    height: int | None = None
    provider: str = ""
    model: str = ""
    created_at: datetime | None = None


class JobRow(SQLModel, table=True):
    __tablename__ = "jobs"

    id: str = Field(primary_key=True)
    project_id: str | None = Field(default=None, index=True)
    shot_id: str | None = Field(default=None, index=True)
    kind: str
    provider: str = ""
    status: str = "pending"
    progress: float = 0.0
    payload_json: str = "{}"
    result_json: str | None = None
    error: str | None = None
    cost_estimate: float | None = None
    cost_actual: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TrackRow(SQLModel, table=True):
    __tablename__ = "tracks"

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True, foreign_key="projects.id")
    source_path: str = ""
    duration_seconds: float | None = None
    bpm: float | None = None
    key: str | None = None
    instrumental_path: str | None = None


class LyricLineRow(SQLModel, table=True):
    __tablename__ = "lyric_lines"

    id: str = Field(primary_key=True)
    track_id: str = Field(index=True, foreign_key="tracks.id")
    index: int
    text: str = ""
    start: float = 0.0
    end: float = 0.0
    words_json: str = "[]"


class VoicePoolVoiceRow(SQLModel, table=True):
    __tablename__ = "voice_pool_voices"

    id: str = Field(primary_key=True)
    proveedor: str = ""
    voice_id_externo: str = ""
    nombre_interno: str = ""
    modelo_tts: str = ""
    atributos_json: str = "{}"
    veces_usada: int = 0
    ultima_historia: str | None = None
