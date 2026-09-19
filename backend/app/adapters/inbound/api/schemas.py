"""Esquemas Pydantic de la API -- el UNICO lugar que traduce dominio -> JSON.
Los routers nunca devuelven una dataclass del dominio directamente."""
from __future__ import annotations

from pydantic import BaseModel

from app.application.ports.provider_health import ProviderHealth
from app.application.use_cases.import_story_project import ImportSummary
from app.application.use_cases.project_queries import ProjectDetail
from app.application.use_cases.provider_queries import ProviderSummary
from app.domain.story.entities import Asset, Chapter, Character, Location, Project, Shot, Voice


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


class ProjectOut(BaseModel):
    id: str
    slug: str
    name: str
    kind: str
    estilo_visual: str
    tono: str
    plataformas: list[str]
    formatos: list[str]
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
            root_path=str(project.root_path),
        )


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


class CharacterOut(BaseModel):
    id: str
    nombre: str
    rol: str
    reference_image_path: str | None

    @classmethod
    def from_domain(cls, character: Character) -> "CharacterOut":
        return cls(
            id=character.id,
            nombre=character.nombre,
            rol=character.rol,
            reference_image_path=str(character.reference_image_path) if character.reference_image_path else None,
        )


class LocationOut(BaseModel):
    id: str
    nombre: str
    descripcion_fija: str
    reference_image_path: str | None

    @classmethod
    def from_domain(cls, location: Location) -> "LocationOut":
        return cls(
            id=location.id,
            nombre=location.nombre,
            descripcion_fija=location.descripcion_fija,
            reference_image_path=str(location.reference_image_path) if location.reference_image_path else None,
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
    def from_domain(cls, shot: Shot, assets_by_shot_id: dict[str, list[Asset]]) -> "ShotOut":
        related = assets_by_shot_id.get(shot.id, [])
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
