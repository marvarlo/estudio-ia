import uuid

import pytest

from app.application.ports.tts import TTSRequest, TTSResult
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.generate_shot_audio import GenerateShotAudioUseCase
from app.application.use_cases.shot_editing import CreateShotUseCase, ShotInput
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.story.entities import Character, Voice


class FakeTTSPort:
    def __init__(self) -> None:
        self.last_request: TTSRequest | None = None

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        self.last_request = request
        return TTSResult(audio_bytes=b"fake-mp3-bytes", provider="fake", model="fake-model")

    async def health_check(self):  # pragma: no cover
        raise NotImplementedError


def _setup(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Audio Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    repository.save_character(Character(id="char-1", project_id=project.id, slug="protagonista_01", nombre="Vera"))
    repository.save_voice(
        Voice(id=str(uuid.uuid4()), project_id=project.id, personaje_id=None, proveedor="ElevenLabs", voice_id_externo="narrador-voice")
    )
    repository.save_voice(
        Voice(id=str(uuid.uuid4()), project_id=project.id, personaje_id="protagonista_01", proveedor="ElevenLabs", voice_id_externo="vera-voice")
    )
    return project, chapter


async def test_uses_character_voice_when_shot_has_a_personaje(tmp_path, repository):
    project, chapter = _setup(tmp_path, repository)
    shot = CreateShotUseCase(repository).execute(
        chapter.id, ShotInput(tipo="Dialogo", texto="Hola", personaje_ids=["protagonista_01"])
    )
    fake_port = FakeTTSPort()

    asset = await GenerateShotAudioUseCase(repository, fake_port).execute(shot.id)

    assert fake_port.last_request.voice_id == "vera-voice"
    assert asset.path.exists()
    assert asset.path.suffix == ".mp3"
    reloaded_shot = repository.get_shot(shot.id)
    assert reloaded_shot.selected_audio_asset_id == asset.id


async def test_falls_back_to_narrator_when_no_personaje(tmp_path, repository):
    project, chapter = _setup(tmp_path, repository)
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="Narracion sin personajes"))
    fake_port = FakeTTSPort()

    await GenerateShotAudioUseCase(repository, fake_port).execute(shot.id)

    assert fake_port.last_request.voice_id == "narrador-voice"


async def test_raises_when_no_voices_assigned_at_all(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Sin Voces")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="x"))
    fake_port = FakeTTSPort()

    with pytest.raises(ValueError, match="voz"):
        await GenerateShotAudioUseCase(repository, fake_port).execute(shot.id)
