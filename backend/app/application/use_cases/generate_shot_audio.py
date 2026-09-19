"""Genera el audio de UN shot puntual (comando `crear-audio` del skill
original, fila por fila, encolado como Job). Resuelve la voz igual que
build_prompts.py: `Shot.voice_id` explicito si esta seteado, si no la voz
del primer personaje en escena, si no la del narrador."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.adapters.outbound.tts.audio_format import detect_audio_extension
from app.application.ports.repository import ProjectRepositoryPort
from app.application.ports.tts import TTSPort, TTSRequest
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset, Voice

# Los audio tags de ElevenLabs ([whispers], [sighs], etc., ver
# references/audio_tags_elevenlabs.md del skill original) son instrucciones
# PARA el motor de voz -- el texto enviado a la API los incluye tal cual, sin
# limpiar. Solo el subtitulo quemado en Remotion los limpia (build_scenes.py),
# no el audio.


def _resolve_voice(shot, characters_by_slug, voices_by_personaje: dict[str | None, Voice]) -> Voice | None:
    if shot.voice_id:
        for voice in voices_by_personaje.values():
            if voice.voice_id_externo == shot.voice_id:
                return voice
    for personaje_id in shot.personaje_ids:
        if personaje_id in voices_by_personaje:
            return voices_by_personaje[personaje_id]
    return voices_by_personaje.get(None)  # narrador


class GenerateShotAudioUseCase:
    def __init__(self, repository: ProjectRepositoryPort, tts_port: TTSPort) -> None:
        self._repository = repository
        self._tts_port = tts_port

    async def execute(self, shot_id: str, *, select: bool = True) -> Asset:
        shot = self._repository.get_shot(shot_id)
        if shot is None:
            raise ValueError(f"Shot no encontrado: {shot_id}")
        chapter = self._repository.get_chapter(shot.chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {shot.chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")

        characters_by_slug = {c.slug: c for c in self._repository.list_characters(project.id)}
        voices_by_personaje = {v.personaje_id: v for v in self._repository.list_voices(project.id)}
        voice = _resolve_voice(shot, characters_by_slug, voices_by_personaje)
        if voice is None:
            raise ValueError("No hay ninguna voz asignada (ni de personaje ni narrador) -- asigna voces primero")

        result = await self._tts_port.synthesize(
            TTSRequest(text=shot.texto, voice_id=voice.voice_id_externo, model=voice.modelo_tts or None)
        )

        audio_dir = project.root_path / f"capitulo-{chapter.numero}" / "assets" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        # Lemonade (MOSS-TTS-Local) devuelve WAV real aunque se pida
        # `Accept: audio/mpeg` -- verificado en vivo, ver audio_format.py --
        # asi que la extension se decide por el contenido, no por el
        # proveedor pedido.
        extension = detect_audio_extension(result.audio_bytes)
        output_path = audio_dir / f"capitulo{chapter.numero}-escena{shot.orden:02d}-{uuid.uuid4().hex[:8]}{extension}"
        output_path.write_bytes(result.audio_bytes)

        asset = Asset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            chapter_id=chapter.id,
            shot_id=shot.id,
            kind=AssetKind.AUDIO,
            path=output_path,
            provider=result.provider,
            model=result.model,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        if select:
            shot.selected_audio_asset_id = asset.id
            self._repository.save_shot(shot)

        return asset
