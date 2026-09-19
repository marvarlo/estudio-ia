import uuid
from datetime import datetime, timezone

import pytest

from app.application.ports.media_probe import MediaInfo
from app.application.ports.video_generation import VideoGenerationRequest, VideoGenerationResult
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.generate_shot_video import GenerateShotVideoUseCase
from app.application.use_cases.shot_editing import CreateShotUseCase, ShotInput
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset


class FakeVideoPort:
    def __init__(self) -> None:
        self.last_request: VideoGenerationRequest | None = None

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResult:
        self.last_request = request
        return VideoGenerationResult(video_bytes=b"fake-mp4-bytes", provider="fake", model="fake-model")

    async def health_check(self):  # pragma: no cover
        raise NotImplementedError


class FakeMediaProbe:
    def __init__(self, duration: float = 6.5) -> None:
        self.duration = duration

    def probe(self, path):
        return MediaInfo(duration_seconds=self.duration)


def _setup_with_image(tmp_path, repository, *, with_audio: bool):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Video Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="x", prompt_video="accion dramatica"))

    image_asset = Asset(
        id=str(uuid.uuid4()), project_id=project.id, chapter_id=chapter.id, shot_id=shot.id,
        kind=AssetKind.IMAGE, path=tmp_path / "shot.png", width=1280, height=720, created_at=datetime.now(timezone.utc),
    )
    (tmp_path / "shot.png").write_bytes(b"fake-png")
    repository.save_asset(image_asset)
    shot.selected_image_asset_id = image_asset.id

    if with_audio:
        audio_asset = Asset(
            id=str(uuid.uuid4()), project_id=project.id, chapter_id=chapter.id, shot_id=shot.id,
            kind=AssetKind.AUDIO, path=tmp_path / "shot.mp3", created_at=datetime.now(timezone.utc),
        )
        (tmp_path / "shot.mp3").write_bytes(b"fake-mp3")
        repository.save_asset(audio_asset)
        shot.selected_audio_asset_id = audio_asset.id

    repository.save_shot(shot)
    return project, chapter, shot


async def test_video_without_audio_requirement_uses_image_only(tmp_path, repository):
    project, chapter, shot = _setup_with_image(tmp_path, repository, with_audio=False)
    fake_port = FakeVideoPort()

    asset = await GenerateShotVideoUseCase(repository, fake_port, FakeMediaProbe(), requires_audio=False).execute(shot.id)

    assert fake_port.last_request.driving_audio_path is None
    assert asset.kind == AssetKind.VIDEO
    assert asset.path.exists()
    reloaded_shot = repository.get_shot(shot.id)
    assert reloaded_shot.selected_video_asset_id == asset.id


async def test_video_requiring_audio_uses_real_probed_duration(tmp_path, repository):
    project, chapter, shot = _setup_with_image(tmp_path, repository, with_audio=True)
    fake_port = FakeVideoPort()
    probe = FakeMediaProbe(duration=7.25)

    await GenerateShotVideoUseCase(repository, fake_port, probe, requires_audio=True).execute(shot.id)

    assert fake_port.last_request.driving_audio_path is not None
    assert fake_port.last_request.duration_seconds == 7.25


async def test_video_requiring_audio_raises_without_selected_audio(tmp_path, repository):
    project, chapter, shot = _setup_with_image(tmp_path, repository, with_audio=False)
    fake_port = FakeVideoPort()

    with pytest.raises(ValueError, match="audio"):
        await GenerateShotVideoUseCase(repository, fake_port, FakeMediaProbe(), requires_audio=True).execute(shot.id)


async def test_video_raises_without_selected_image(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Sin Imagen")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="x"))
    fake_port = FakeVideoPort()

    with pytest.raises(ValueError, match="imagen"):
        await GenerateShotVideoUseCase(repository, fake_port, FakeMediaProbe(), requires_audio=False).execute(shot.id)
