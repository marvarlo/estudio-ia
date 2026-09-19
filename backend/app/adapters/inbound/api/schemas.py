"""Esquemas Pydantic de la API -- el UNICO lugar que traduce dominio -> JSON.
Los routers nunca devuelven una dataclass del dominio directamente."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.application.ports.provider_health import ProviderHealth
from app.application.use_cases.import_story_project import ImportSummary
from app.application.use_cases.lint import LintWarning
from app.application.use_cases.project_queries import ProjectDetail
from app.application.use_cases.provider_queries import ProviderSummary
from app.application.use_cases.story_generation import CastGenerationResult
from app.domain.story.entities import (
    Asset,
    Canon,
    Chapter,
    Character,
    Location,
    Project,
    Shot,
    Voice,
    VoicePoolVoice,
)

# ---------------------------------------------------------------------------
# Import (fase 0)
# ---------------------------------------------------------------------------


class ImportRequest(BaseModel):
    path: str


class ImportSummaryOut(BaseModel):
    project_id: str
    slug: str
    name: str
    chapters_imported: int
    shots_imported: int
    characters_imported: int
    locations_imported: int
    voices_imported: int
    assets_found: int
    warnings: list[str]

    @classmethod
    def from_domain(cls, summary: ImportSummary) -> "ImportSummaryOut":
        return cls(**summary.__dict__)


# ---------------------------------------------------------------------------
# Project / Canon / Cast (fase 1)
# ---------------------------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    name: str
    estilo_visual: str = "anime"
    tono: str = "NORMAL"
    plataformas: list[str] = Field(default_factory=lambda: ["YouTube"])


class ProjectOut(BaseModel):
    id: str
    slug: str
    name: str
    kind: str
    estilo_visual: str
    tono: str
    plataformas: list[str]
    formatos: list[str]
    num_episodios: int | None
    duracion_objetivo_min: int | None
    root_path: str

    @classmethod
    def from_domain(cls, project: Project) -> "ProjectOut":
        return cls(
            id=project.id,
            slug=project.slug,
            name=project.name,
            kind=project.kind.value,
            estilo_visual=project.estilo_visual,
            tono=project.tono.value,
            plataformas=project.plataformas,
            formatos=project.formatos,
            num_episodios=project.num_episodios,
            duracion_objetivo_min=project.duracion_objetivo_min,
            root_path=str(project.root_path),
        )


class CanonGenerateRequest(BaseModel):
    estilo_narrativo: str
    tono: str = "NORMAL"
    plataformas: list[str] = Field(default_factory=lambda: ["YouTube"])
    estilo_visual: str = "anime"
    num_episodios: int = 10
    duracion_objetivo_min: int = 10
    semilla: str = ""
    provider_id: str = "lemonade-text"


class SeasonEpisodeOut(BaseModel):
    numero: int
    resumen: str
    cliffhanger: str


class CanonOut(BaseModel):
    logline: str
    premisa: str
    reglas_sistema: str
    glosario: str
    temporada: list[SeasonEpisodeOut]
    raw_markdown: str

    @classmethod
    def from_domain(cls, canon: Canon) -> "CanonOut":
        return cls(
            logline=canon.logline,
            premisa=canon.premisa,
            reglas_sistema=canon.reglas_sistema,
            glosario=canon.glosario,
            temporada=[SeasonEpisodeOut(numero=ep.numero, resumen=ep.resumen, cliffhanger=ep.cliffhanger) for ep in canon.temporada],
            raw_markdown=canon.raw_markdown,
        )


class CastGenerateRequest(BaseModel):
    num_personajes: int = 5
    num_escenarios: int = 4
    notas: str = ""
    provider_id: str = "lemonade-text"


class CharacterOut(BaseModel):
    id: str
    slug: str
    nombre: str
    rol: str
    tokens_visuales: dict
    reference_image_path: str | None

    @classmethod
    def from_domain(cls, character: Character) -> "CharacterOut":
        return cls(
            id=character.id,
            slug=character.slug,
            nombre=character.nombre,
            rol=character.rol,
            tokens_visuales=character.tokens_visuales,
            reference_image_path=str(character.reference_image_path) if character.reference_image_path else None,
        )


class LocationOut(BaseModel):
    id: str
    slug: str
    nombre: str
    descripcion_fija: str
    reference_image_path: str | None

    @classmethod
    def from_domain(cls, location: Location) -> "LocationOut":
        return cls(
            id=location.id,
            slug=location.slug,
            nombre=location.nombre,
            descripcion_fija=location.descripcion_fija,
            reference_image_path=str(location.reference_image_path) if location.reference_image_path else None,
        )


class CastGenerationOut(BaseModel):
    characters: list[CharacterOut]
    locations: list[LocationOut]

    @classmethod
    def from_domain(cls, result: CastGenerationResult) -> "CastGenerationOut":
        return cls(
            characters=[CharacterOut.from_domain(c) for c in result.characters],
            locations=[LocationOut.from_domain(l) for l in result.locations],
        )


class VoiceOut(BaseModel):
    id: str
    personaje_id: str | None
    proveedor: str
    voice_id_externo: str
    notas_direccion: str

    @classmethod
    def from_domain(cls, voice: Voice) -> "VoiceOut":
        return cls(
            id=voice.id,
            personaje_id=voice.personaje_id,
            proveedor=voice.proveedor,
            voice_id_externo=voice.voice_id_externo,
            notas_direccion=voice.notas_direccion,
        )


class ProjectDetailOut(BaseModel):
    project: ProjectOut
    logline: str
    chapters: list[ChapterOut]
    characters: list[CharacterOut]
    locations: list[LocationOut]
    voices: list[VoiceOut]

    @classmethod
    def from_domain(cls, detail: ProjectDetail) -> "ProjectDetailOut":
        return cls(
            project=ProjectOut.from_domain(detail.project),
            logline=detail.canon.logline if detail.canon else "",
            chapters=[ChapterOut.from_domain(c) for c in detail.chapters],
            characters=[CharacterOut.from_domain(c) for c in detail.characters],
            locations=[LocationOut.from_domain(l) for l in detail.locations],
            voices=[VoiceOut.from_domain(v) for v in detail.voices],
        )


# ---------------------------------------------------------------------------
# Chapters / Shots
# ---------------------------------------------------------------------------


class ChapterCreateRequest(BaseModel):
    project_id: str
    titulo: str
    numero: int | None = None


class ChapterOut(BaseModel):
    id: str
    numero: int
    titulo: str
    estado: str
    tiene_prosa: bool

    @classmethod
    def from_domain(cls, chapter: Chapter) -> "ChapterOut":
        return cls(
            id=chapter.id,
            numero=chapter.numero,
            titulo=chapter.titulo,
            estado=chapter.estado.value,
            tiene_prosa=chapter.prosa_path is not None,
        )


class ShotWriteRequest(BaseModel):
    tipo: str = "Narracion"
    personaje_ids: list[str] = Field(default_factory=list)
    escenario_id: str | None = None
    sub_escenario: str = ""
    momento_dia: str = ""
    texto: str = ""
    prompt_imagen: str = ""
    prompt_video: str = ""
    movimiento_camara: str = ""
    duracion_estimada_seg: float | None = None
    sfx_musica: str = ""


class ShotOut(BaseModel):
    id: str
    orden: int
    tipo: str
    personaje_ids: list[str]
    escenario_id: str | None
    sub_escenario: str
    momento_dia: str
    texto: str
    prompt_imagen: str
    prompt_video: str
    movimiento_camara: str
    duracion_estimada_seg: float | None
    sfx_musica: str
    image_asset_path: str | None
    audio_asset_path: str | None
    video_asset_path: str | None

    @classmethod
    def from_domain(cls, shot: Shot, assets_by_shot_id: dict[str, list[Asset]] | None = None) -> "ShotOut":
        related = (assets_by_shot_id or {}).get(shot.id, [])
        image_path = next((str(a.path) for a in related if a.kind.value == "image"), None)
        audio_path = next((str(a.path) for a in related if a.kind.value == "audio"), None)
        video_path = next((str(a.path) for a in related if a.kind.value == "video"), None)
        return cls(
            id=shot.id,
            orden=shot.orden,
            tipo=shot.tipo.value,
            personaje_ids=shot.personaje_ids,
            escenario_id=shot.escenario_id,
            sub_escenario=shot.sub_escenario,
            momento_dia=shot.momento_dia,
            texto=shot.texto,
            prompt_imagen=shot.prompt_imagen,
            prompt_video=shot.prompt_video,
            movimiento_camara=shot.movimiento_camara,
            duracion_estimada_seg=shot.duracion_estimada_seg,
            sfx_musica=shot.sfx_musica,
            image_asset_path=image_path,
            audio_asset_path=audio_path,
            video_asset_path=video_path,
        )


class ChapterShotsOut(BaseModel):
    chapter: ChapterOut
    shots: list[ShotOut]

    @classmethod
    def from_domain(cls, chapter: Chapter, shots: list[Shot], assets: list[Asset]) -> "ChapterShotsOut":
        assets_by_shot_id: dict[str, list[Asset]] = {}
        for asset in assets:
            if asset.shot_id:
                assets_by_shot_id.setdefault(asset.shot_id, []).append(asset)
        return cls(
            chapter=ChapterOut.from_domain(chapter),
            shots=[ShotOut.from_domain(s, assets_by_shot_id) for s in shots],
        )


class ReorderShotsRequest(BaseModel):
    ordered_shot_ids: list[str]


class LintWarningOut(BaseModel):
    severity: str
    message: str
    shot_id: str | None

    @classmethod
    def from_domain(cls, warning: LintWarning) -> "LintWarningOut":
        return cls(severity=warning.severity, message=warning.message, shot_id=warning.shot_id)


class ExportOut(BaseModel):
    path: str


# ---------------------------------------------------------------------------
# Voice pool / sheets
# ---------------------------------------------------------------------------


class VoicePoolAddRequest(BaseModel):
    proveedor: str
    voice_id_externo: str
    nombre_interno: str = ""
    modelo_tts: str = ""
    atributos: dict = Field(default_factory=dict)


class VoicePoolVoiceOut(BaseModel):
    id: str
    proveedor: str
    voice_id_externo: str
    nombre_interno: str
    modelo_tts: str
    atributos: dict
    veces_usada: int
    ultima_historia: str | None

    @classmethod
    def from_domain(cls, voice: VoicePoolVoice) -> "VoicePoolVoiceOut":
        return cls(**voice.__dict__)


class SheetGenerateRequest(BaseModel):
    provider_id: str = "lemonade-image"


class AssetOut(BaseModel):
    id: str
    kind: str
    path: str
    width: int | None
    height: int | None
    provider: str
    model: str

    @classmethod
    def from_domain(cls, asset: Asset) -> "AssetOut":
        return cls(
            id=asset.id,
            kind=asset.kind.value,
            path=str(asset.path),
            width=asset.width,
            height=asset.height,
            provider=asset.provider,
            model=asset.model,
        )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class ProviderOut(BaseModel):
    id: str
    name: str
    kind: str
    capabilities: list[str]
    configured: bool

    @classmethod
    def from_domain(cls, summary: ProviderSummary) -> "ProviderOut":
        return cls(**summary.__dict__)


class ProviderHealthOut(BaseModel):
    ok: bool
    detail: str
    latency_ms: float | None

    @classmethod
    def from_domain(cls, health: ProviderHealth) -> "ProviderHealthOut":
        return cls(ok=health.ok, detail=health.detail, latency_ms=health.latency_ms)
