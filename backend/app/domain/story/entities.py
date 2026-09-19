"""Entidades del dominio de 'historia' (motion comic narrado).

Dataclasses puras -- sin Pydantic ni SQLModel. El mapeo a JSON (API) vive en
adapters/inbound/api/schemas.py; el mapeo a tablas vive en
adapters/outbound/repository/models.py. El dominio no sabe que existen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.domain.shared.value_objects import ChapterStatus, ProjectKind, ShotType, Tone, AssetKind


@dataclass
class Project:
    id: str
    slug: str
    name: str
    kind: ProjectKind
    root_path: Path
    estilo_visual: str = "anime"
    tono: Tone = Tone.NORMAL
    plataformas: list[str] = field(default_factory=list)
    formatos: list[str] = field(default_factory=list)  # ej. ["1280x720", "940x1672"]
    num_episodios: int | None = None
    duracion_objetivo_min: int | None = None
    created_at: datetime | None = None


@dataclass
class SeasonEpisode:
    """Una fila del esqueleto de temporada (seccion 6 de canon.md): una
    linea + cliffhanger por capitulo, decidido antes de escribir prosa."""

    numero: int
    resumen: str
    cliffhanger: str


@dataclass
class Canon:
    project_id: str
    logline: str = ""
    premisa: str = ""
    reglas_sistema: str = ""
    glosario: str = ""
    temporada: list[SeasonEpisode] = field(default_factory=list)
    raw_markdown: str = ""


@dataclass
class Chapter:
    id: str
    project_id: str
    numero: int
    titulo: str
    prosa_path: Path | None = None
    produccion_path: Path | None = None
    estado: ChapterStatus = ChapterStatus.BORRADOR


@dataclass
class Shot:
    """Una fila de produccion.md. Es la unidad central del dominio: en musica
    (fases posteriores) el mismo concepto cubre una ventana de la cancion."""

    id: str
    chapter_id: str
    orden: int
    tipo: ShotType
    personaje_ids: list[str] = field(default_factory=list)
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
    selected_image_asset_id: str | None = None
    selected_audio_asset_id: str | None = None
    selected_video_asset_id: str | None = None


@dataclass
class Character:
    """`slug` es el id LEGIBLE (`protagonista_01`) que usan produccion.md
    (`Shot.personaje_ids`), los `[id]` entre corchetes de `Prompt Imagen`, y
    personajes.json -- distinto de `id`, la clave primaria interna de la
    base de datos. Los dos existen porque el primero es estable entre
    reimportaciones/regeneraciones y legible por humanos; el segundo es solo
    un detalle de persistencia."""

    id: str
    project_id: str
    slug: str
    nombre: str
    rol: str = ""
    prompt_anchor: str = ""
    tokens_visuales: dict = field(default_factory=dict)
    voice_id: str | None = None
    reference_image_path: Path | None = None


@dataclass
class Location:
    id: str
    project_id: str
    slug: str
    nombre: str
    descripcion_fija: str = ""
    reference_image_path: Path | None = None


@dataclass
class Voice:
    id: str
    project_id: str
    personaje_id: str | None
    proveedor: str
    voice_id_externo: str
    modelo_tts: str = ""
    notas_direccion: str = ""


@dataclass
class Asset:
    """Cada generacion crea un Asset nuevo (nunca sobreescribe); el Shot
    apunta al seleccionado via selected_*_asset_id -- ver seccion 3 del doc
    de arquitectura ('Regla de versionado')."""

    id: str
    project_id: str
    kind: AssetKind
    path: Path
    chapter_id: str | None = None
    shot_id: str | None = None
    width: int | None = None
    height: int | None = None
    provider: str = ""
    model: str = ""
    created_at: datetime | None = None


@dataclass
class VoicePoolVoice:
    """Pool de voces a nivel CANAL (no por proyecto) -- voces_pool.json del
    skill original. Persiste entre historias para no repetir el mismo timbre
    de protagonista; ver Paso 8 de SKILL.md."""

    id: str
    proveedor: str
    voice_id_externo: str
    nombre_interno: str = ""
    modelo_tts: str = ""
    atributos: dict = field(default_factory=dict)  # timbre, edad_percibida, energia, genero_percibido
    veces_usada: int = 0
    ultima_historia: str | None = None
