"""Renderiza el video final de UN capitulo (sidecar Remotion, fase 3):
arma `timeline.json` a partir de los shots ya generados (imagen+audio o
video por shot, con la duracion REAL medida via MediaProbePort -- misma
idea que build_scenes.py del skill original) y se lo pasa a RenderPort.

Cada render crea un Asset NUEVO (nunca sobreescribe), igual que la regla de
versionado de la fase 2 -- `Chapter.selected_render_asset_id` guarda cual es
el render vigente."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.application.ports.media_probe import MediaProbePort
from app.application.ports.render import RenderPort, RenderRequest
from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import AssetKind, ChapterStatus
from app.domain.story.entities import Asset, Shot

# Los audio tags de ElevenLabs ([thoughtful], [sighs], etc.) son instrucciones
# para el motor de voz, no texto para el espectador -- el subtitulo quemado
# debe mostrar el texto limpio (misma regex que build_scenes.py del skill).
_TAG_RE = re.compile(r"\s*\[[^\]]*\]\s*")

DEFAULT_WIDTH, DEFAULT_HEIGHT = 1920, 1080


def _clean_subtitle(texto: str) -> str:
    sin_tags = _TAG_RE.sub(" ", texto)
    return re.sub(r"\s+", " ", sin_tags).strip()


def _relative_to_public_dir(path: Path, public_dir: Path) -> str:
    try:
        return path.resolve().relative_to(public_dir.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(
            f"El asset {path} no vive bajo la carpeta de assets del capitulo ({public_dir}) -- "
            "no se puede servir como staticFile() de Remotion."
        ) from exc


@dataclass
class ChapterTimeline:
    timeline: dict[str, Any]
    public_dir: Path
    width: int
    height: int


class BuildChapterTimelineUseCase:
    """Solo arma la estructura -- no renderiza nada. Separado de
    RenderChapterUseCase para poder testear el mapeo shot->escena sin
    invocar Remotion ni el filesystem de salida."""

    def __init__(self, repository: ProjectRepositoryPort, media_probe: MediaProbePort) -> None:
        self._repository = repository
        self._media_probe = media_probe

    def execute(self, chapter_id: str) -> ChapterTimeline:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")
        shots = self._repository.list_shots(chapter_id)
        if not shots:
            raise ValueError("Este capitulo todavia no tiene shots -- no hay nada que renderizar")
        assets_by_id = {a.id: a for a in self._repository.list_assets(project.id, chapter_id=chapter_id)}

        public_dir = project.root_path / f"capitulo-{chapter.numero}" / "assets"
        width = height = None
        escenas: list[dict[str, Any]] = []

        for shot in sorted(shots, key=lambda s: s.orden):
            escena, shot_width, shot_height = self._build_escena(shot, assets_by_id, public_dir)
            escenas.append(escena)
            if width is None and shot_width and shot_height:
                width, height = shot_width, shot_height

        is_last_episode = project.num_episodios is not None and chapter.numero >= project.num_episodios
        timeline = {
            "meta": {
                "canal": project.name,
                "tagline": "",
                "numeroCapitulo": chapter.numero,
                "tituloCapitulo": chapter.titulo or None,
                "outroLabel": "Fin" if is_last_episode else "Continuará",
                "width": width or DEFAULT_WIDTH,
                "height": height or DEFAULT_HEIGHT,
            },
            "escenas": escenas,
        }
        return ChapterTimeline(timeline=timeline, public_dir=public_dir, width=width or DEFAULT_WIDTH, height=height or DEFAULT_HEIGHT)

    def _build_escena(
        self, shot: Shot, assets_by_id: dict[str, Asset], public_dir: Path
    ) -> tuple[dict[str, Any], int | None, int | None]:
        image_asset = assets_by_id.get(shot.selected_image_asset_id) if shot.selected_image_asset_id else None
        audio_asset = assets_by_id.get(shot.selected_audio_asset_id) if shot.selected_audio_asset_id else None
        video_asset = assets_by_id.get(shot.selected_video_asset_id) if shot.selected_video_asset_id else None

        if video_asset is not None:
            duration = self._media_probe.probe(video_asset.path).duration_seconds
            if duration is None:
                raise ValueError(f"No se pudo medir la duracion real del video de la escena {shot.orden:02d} ({video_asset.path})")
            return (
                {
                    "numero": f"{shot.orden:02d}",
                    "tipo": shot.tipo.value,
                    "texto": shot.texto,
                    "subtitulo": _clean_subtitle(shot.texto),
                    "movimiento_camara": shot.movimiento_camara,
                    "imagen": None,
                    "audio": None,
                    "video": _relative_to_public_dir(video_asset.path, public_dir),
                    "durationInSeconds": round(duration, 3),
                },
                video_asset.width,
                video_asset.height,
            )

        if image_asset is None or audio_asset is None:
            raise ValueError(
                f"La escena {shot.orden:02d} no tiene imagen+audio seleccionados ni un video -- "
                "genera los assets faltantes antes de renderizar el capitulo"
            )
        duration = self._media_probe.probe(audio_asset.path).duration_seconds
        if duration is None:
            raise ValueError(f"No se pudo medir la duracion real del audio de la escena {shot.orden:02d} ({audio_asset.path})")
        return (
            {
                "numero": f"{shot.orden:02d}",
                "tipo": shot.tipo.value,
                "texto": shot.texto,
                "subtitulo": _clean_subtitle(shot.texto),
                "movimiento_camara": shot.movimiento_camara,
                "imagen": _relative_to_public_dir(image_asset.path, public_dir),
                "audio": _relative_to_public_dir(audio_asset.path, public_dir),
                "video": None,
                "durationInSeconds": round(duration, 3),
            },
            image_asset.width,
            image_asset.height,
        )


class RenderChapterUseCase:
    def __init__(self, repository: ProjectRepositoryPort, render_port: RenderPort, media_probe: MediaProbePort) -> None:
        self._repository = repository
        self._render_port = render_port
        self._timeline_use_case = BuildChapterTimelineUseCase(repository, media_probe)

    async def execute(self, chapter_id: str) -> Asset:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")

        built = self._timeline_use_case.execute(chapter_id)

        render_dir = project.root_path / f"capitulo-{chapter.numero}" / "assets" / "render"
        render_dir.mkdir(parents=True, exist_ok=True)
        output_path = render_dir / f"capitulo{chapter.numero}-{uuid.uuid4().hex[:8]}.mp4"

        result = await self._render_port.render(
            RenderRequest(
                composition_id="Capitulo",
                timeline=built.timeline,
                output_path=output_path,
                public_dir=built.public_dir,
            )
        )

        asset = Asset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            chapter_id=chapter.id,
            shot_id=None,
            kind=AssetKind.VIDEO,
            path=result.output_path,
            width=built.width,
            height=built.height,
            provider="remotion",
            model="Capitulo",
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        chapter.selected_render_asset_id = asset.id
        chapter.estado = ChapterStatus.RENDERIZADO
        self._repository.save_chapter(chapter)

        return asset
