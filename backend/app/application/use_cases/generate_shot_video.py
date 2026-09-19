"""Anima UN shot puntual (comandos `crear-video-animado` / `crear-video-omni`
del skill original) a partir de la imagen ya seleccionada (y, para
proveedores con lip-sync real como WAN, el audio ya seleccionado)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.application.ports.media_probe import MediaProbePort
from app.application.ports.repository import ProjectRepositoryPort
from app.application.ports.video_generation import VideoGenerationPort, VideoGenerationRequest
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset

DEFAULT_DURATION_SECONDS = 5.0


class GenerateShotVideoUseCase:
    def __init__(
        self,
        repository: ProjectRepositoryPort,
        video_port: VideoGenerationPort,
        media_probe: MediaProbePort,
        requires_audio: bool,
    ) -> None:
        """`requires_audio`: True para WAN (lip-sync real, necesita el audio
        ya generado como driving signal); False para Veo/Omni (no aceptan
        audio de referencia -- el video sale mudo/con audio inventado, y el
        audio real se mezcla despues en el render final, fuera de este caso
        de uso)."""
        self._repository = repository
        self._video_port = video_port
        self._media_probe = media_probe
        self._requires_audio = requires_audio

    async def execute(self, shot_id: str, *, select: bool = True) -> Asset:
        shot = self._repository.get_shot(shot_id)
        if shot is None:
            raise ValueError(f"Shot no encontrado: {shot_id}")
        if not shot.selected_image_asset_id:
            raise ValueError("Este shot todavia no tiene una imagen seleccionada -- genera la imagen primero")
        chapter = self._repository.get_chapter(shot.chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {shot.chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")

        image_assets = {a.id: a for a in self._repository.list_assets(project.id, chapter_id=chapter.id)}
        image_asset = image_assets.get(shot.selected_image_asset_id)
        if image_asset is None:
            raise ValueError("El asset de imagen seleccionado ya no existe")

        audio_path = None
        duration_seconds = shot.duracion_estimada_seg or DEFAULT_DURATION_SECONDS
        if self._requires_audio:
            if not shot.selected_audio_asset_id:
                raise ValueError("Este proveedor de video necesita audio real (lip-sync) -- genera el audio primero")
            audio_asset = image_assets.get(shot.selected_audio_asset_id)
            if audio_asset is None:
                raise ValueError("El asset de audio seleccionado ya no existe")
            audio_path = audio_asset.path
            media_info = self._media_probe.probe(audio_path)
            if media_info.duration_seconds:
                duration_seconds = media_info.duration_seconds

        request = VideoGenerationRequest(
            prompt=shot.prompt_video or shot.prompt_imagen or shot.texto,
            image_path=image_asset.path,
            driving_audio_path=audio_path,
            duration_seconds=duration_seconds,
            width=image_asset.width or 1280,
            height=image_asset.height or 720,
        )
        result = await self._video_port.generate(request)

        video_dir = project.root_path / f"capitulo-{chapter.numero}" / "assets" / f"{image_asset.width}x{image_asset.height}" / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        output_path = video_dir / f"capitulo{chapter.numero}-escena{shot.orden:02d}-{uuid.uuid4().hex[:8]}.mp4"
        output_path.write_bytes(result.video_bytes)

        asset = Asset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            chapter_id=chapter.id,
            shot_id=shot.id,
            kind=AssetKind.VIDEO,
            path=output_path,
            width=image_asset.width,
            height=image_asset.height,
            provider=result.provider,
            model=result.model,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        if select:
            shot.selected_video_asset_id = asset.id
            self._repository.save_shot(shot)

        return asset
