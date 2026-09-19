"""Renderiza LyricsVideo o Karaoke (fase 4) -- comparte RenderPort con
RenderChapterUseCase (fase 3), pero arma un timeline distinto: en vez de
audio propio por shot, hay UNA pista maestra (`audio`) que suena de punta a
punta, y cada shot se posiciona en su ventana de tiempo REAL (`start`/`end`
tomados de la letra transcrita) en vez de encadenarse secuencialmente con
pausas de 1s -- insertar pausas aca desincronizaria el video del audio real.
`lyrics` viaja aparte con las palabras y sus tiempos para el resaltado de
Karaoke (ver render/src/Lyrics.tsx)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.application.ports.media_probe import MediaProbePort
from app.application.ports.render import RenderPort, RenderRequest
from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import AssetKind, ChapterStatus
from app.domain.story.entities import Asset

DEFAULT_WIDTH, DEFAULT_HEIGHT = 1920, 1080
OUTRO_BUFFER_SECONDS = 2.0


def _relative_to_public_dir(path: Path, public_dir: Path) -> str:
    try:
        return path.resolve().relative_to(public_dir.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"El asset {path} no vive bajo la carpeta de assets del track ({public_dir})") from exc


class BuildMusicTimelineUseCase:
    def __init__(self, repository: ProjectRepositoryPort, media_probe: MediaProbePort) -> None:
        self._repository = repository
        self._media_probe = media_probe

    def execute(self, chapter_id: str, track_id: str) -> tuple[dict[str, Any], Path, int, int]:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")
        track = self._repository.get_track(track_id)
        if track is None:
            raise ValueError(f"Pista no encontrada: {track_id}")
        shots = self._repository.list_shots(chapter_id)
        if not shots:
            raise ValueError("Este track todavia no tiene shots generados a partir de la letra")
        lines = self._repository.list_lyric_lines(track_id)
        assets_by_id = {a.id: a for a in self._repository.list_assets(project.id, chapter_id=chapter_id)}

        public_dir = project.root_path / f"capitulo-{chapter.numero}" / "assets"
        track_path = Path(track.source_path)
        track_info = self._media_probe.probe(track_path)
        track_duration = track_info.duration_seconds or track.duration_seconds

        width = height = None
        escenas: list[dict[str, Any]] = []
        ordered_shots = sorted(shots, key=lambda s: s.orden)
        for shot in ordered_shots:
            image_asset = assets_by_id.get(shot.selected_image_asset_id) if shot.selected_image_asset_id else None
            if image_asset is None:
                raise ValueError(f"El shot #{shot.orden} todavia no tiene una imagen de fondo seleccionada")
            if width is None:
                width, height = image_asset.width or DEFAULT_WIDTH, image_asset.height or DEFAULT_HEIGHT

            # `start_seg` es la fuente de verdad del tiempo absoluto de ESTE
            # shot en la pista maestra -- NUNCA se reconstruye buscando la
            # linea de letra en la misma posicion de indice, porque un shot
            # no es necesariamente una linea (el videoclip animado tiene
            # varios shots por ventana de 8s, sin correspondencia 1:1 con
            # las lineas). Bug real encontrado en la fase 5 antes de
            # verificar en vivo: con "una linea = un shot" (lyrics/karaoke)
            # coincidia por casualidad de indice, pero con ventanas de beat
            # generaba tiempos superpuestos/incorrectos.
            if shot.start_seg is None:
                raise ValueError(f"El shot #{shot.orden} no tiene start_seg -- regeneralo desde la letra")
            start = shot.start_seg
            end = start + (shot.duracion_estimada_seg or 3.0)
            escenas.append(
                {
                    "numero": f"{shot.orden:02d}",
                    "texto": shot.texto,
                    "subtitulo": shot.texto,
                    "movimiento_camara": shot.movimiento_camara,
                    "imagen": _relative_to_public_dir(image_asset.path, public_dir),
                    "start": round(start, 3),
                    "end": round(end, 3),
                }
            )

        total_duration = track_duration or (escenas[-1]["end"] + OUTRO_BUFFER_SECONDS if escenas else 0.0)

        timeline = {
            "meta": {
                "canal": project.name,
                "width": width or DEFAULT_WIDTH,
                "height": height or DEFAULT_HEIGHT,
                "durationInSeconds": round(total_duration, 3),
            },
            "audio": {
                "path": _relative_to_public_dir(track_path, public_dir),
                "volume": 1.0,
            },
            "escenas": escenas,
            "lyrics": {
                "lines": [
                    {
                        "text": line.text,
                        "start": round(line.start, 3),
                        "end": round(line.end, 3),
                        "words": [
                            {"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3)}
                            for w in line.words
                        ],
                    }
                    for line in lines
                ],
            },
        }
        return timeline, public_dir, width or DEFAULT_WIDTH, height or DEFAULT_HEIGHT


class RenderMusicVideoUseCase:
    def __init__(self, repository: ProjectRepositoryPort, render_port: RenderPort, media_probe: MediaProbePort) -> None:
        self._repository = repository
        self._render_port = render_port
        self._timeline_use_case = BuildMusicTimelineUseCase(repository, media_probe)

    async def execute(self, chapter_id: str, track_id: str, composition_id: str) -> Any:
        if composition_id not in ("LyricsVideo", "Karaoke", "MusicVideo"):
            raise ValueError(f"composition_id desconocido para musica: {composition_id}")

        chapter = self._repository.get_chapter(chapter_id)
        project = self._repository.get_project(chapter.project_id)

        timeline, public_dir, _width, _height = self._timeline_use_case.execute(chapter_id, track_id)

        render_dir = public_dir / "render"
        render_dir.mkdir(parents=True, exist_ok=True)
        output_path = render_dir / f"{composition_id.lower()}-{uuid.uuid4().hex[:8]}.mp4"

        result = await self._render_port.render(
            RenderRequest(composition_id=composition_id, timeline=timeline, output_path=output_path, public_dir=public_dir)
        )

        asset = Asset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            chapter_id=chapter.id,
            shot_id=None,
            kind=AssetKind.VIDEO,
            path=result.output_path,
            width=timeline["meta"]["width"],
            height=timeline["meta"]["height"],
            provider="remotion",
            model=composition_id,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        chapter.selected_render_asset_id = asset.id
        chapter.estado = ChapterStatus.RENDERIZADO
        self._repository.save_chapter(chapter)

        return asset
