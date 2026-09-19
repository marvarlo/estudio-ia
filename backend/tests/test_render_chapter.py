import uuid
from datetime import datetime, timezone

import pytest

from app.application.ports.media_probe import MediaInfo
from app.application.ports.render import RenderRequest, RenderResult
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.render_chapter import BuildChapterTimelineUseCase, RenderChapterUseCase
from app.application.use_cases.shot_editing import CreateShotUseCase, ShotInput
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.shared.value_objects import AssetKind, ChapterStatus
from app.domain.story.entities import Asset


class FakeMediaProbe:
    def __init__(self, duration: float = 4.0) -> None:
        self.duration = duration

    def probe(self, path):
        return MediaInfo(duration_seconds=self.duration, width=1280, height=720)


class FakeRenderPort:
    def __init__(self) -> None:
        self.last_request: RenderRequest | None = None

    async def render(self, request: RenderRequest) -> RenderResult:
        self.last_request = request
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"fake-mp4")
        return RenderResult(output_path=request.output_path, duration_seconds=42.0)

    async def concat(self, clips, output_path):  # pragma: no cover
        raise NotImplementedError


def _make_project_with_shot(tmp_path, repository, *, texto="Hola [susurra] mundo", numero_episodios=None):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Render Test")
    if numero_episodios is not None:
        project.num_episodios = numero_episodios
        repository.save_project(project)
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="El Comienzo")
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto=texto, movimiento_camara="zoom in lento"))
    return project, chapter, shot


def _attach_image_and_audio(tmp_path, repository, project, chapter, shot):
    assets_dir = project.root_path / f"capitulo-{chapter.numero}" / "assets"
    img_dir = assets_dir / "1280x720" / "imagenes"
    img_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = assets_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    image_path = img_dir / "escena01.png"
    image_path.write_bytes(b"fake-png")
    audio_path = audio_dir / "escena01.mp3"
    audio_path.write_bytes(b"fake-mp3")

    image_asset = Asset(
        id=str(uuid.uuid4()), project_id=project.id, chapter_id=chapter.id, shot_id=shot.id,
        kind=AssetKind.IMAGE, path=image_path, width=1280, height=720, created_at=datetime.now(timezone.utc),
    )
    audio_asset = Asset(
        id=str(uuid.uuid4()), project_id=project.id, chapter_id=chapter.id, shot_id=shot.id,
        kind=AssetKind.AUDIO, path=audio_path, created_at=datetime.now(timezone.utc),
    )
    repository.save_asset(image_asset)
    repository.save_asset(audio_asset)
    shot.selected_image_asset_id = image_asset.id
    shot.selected_audio_asset_id = audio_asset.id
    repository.save_shot(shot)
    return assets_dir


def test_build_timeline_strips_audio_tags_and_resolves_relative_paths(tmp_path, repository):
    project, chapter, shot = _make_project_with_shot(tmp_path, repository, texto="Hola [susurra] mundo")
    assets_dir = _attach_image_and_audio(tmp_path, repository, project, chapter, shot)

    built = BuildChapterTimelineUseCase(repository, FakeMediaProbe(duration=3.5)).execute(chapter.id)

    assert built.public_dir == assets_dir
    assert built.width == 1280 and built.height == 720
    escena = built.timeline["escenas"][0]
    assert escena["subtitulo"] == "Hola mundo"
    assert escena["texto"] == "Hola [susurra] mundo"
    assert escena["imagen"] == "1280x720/imagenes/escena01.png"
    assert escena["audio"] == "audio/escena01.mp3"
    assert escena["video"] is None
    assert escena["durationInSeconds"] == 3.5


def test_build_timeline_outro_label_continuara_by_default(tmp_path, repository):
    project, chapter, shot = _make_project_with_shot(tmp_path, repository, numero_episodios=3)
    _attach_image_and_audio(tmp_path, repository, project, chapter, shot)

    built = BuildChapterTimelineUseCase(repository, FakeMediaProbe()).execute(chapter.id)

    assert built.timeline["meta"]["outroLabel"] == "Continuará"
    assert built.timeline["meta"]["canal"] == project.name


def test_build_timeline_outro_label_fin_on_last_episode(tmp_path, repository):
    project, chapter, shot = _make_project_with_shot(tmp_path, repository, numero_episodios=1)
    _attach_image_and_audio(tmp_path, repository, project, chapter, shot)

    built = BuildChapterTimelineUseCase(repository, FakeMediaProbe()).execute(chapter.id)

    assert built.timeline["meta"]["outroLabel"] == "Fin"


def test_build_timeline_raises_when_shot_missing_assets(tmp_path, repository):
    _, chapter, _shot = _make_project_with_shot(tmp_path, repository)

    with pytest.raises(ValueError, match="imagen\\+audio"):
        BuildChapterTimelineUseCase(repository, FakeMediaProbe()).execute(chapter.id)


async def test_render_chapter_creates_asset_and_marks_selected(tmp_path, repository):
    project, chapter, shot = _make_project_with_shot(tmp_path, repository)
    _attach_image_and_audio(tmp_path, repository, project, chapter, shot)
    fake_render = FakeRenderPort()

    asset = await RenderChapterUseCase(repository, fake_render, FakeMediaProbe()).execute(chapter.id)

    assert asset.kind == AssetKind.VIDEO
    assert asset.shot_id is None
    assert asset.path.exists()
    assert fake_render.last_request.composition_id == "Capitulo"
    assert fake_render.last_request.public_dir == project.root_path / "capitulo-1" / "assets"

    reloaded_chapter = repository.get_chapter(chapter.id)
    assert reloaded_chapter.selected_render_asset_id == asset.id
    assert reloaded_chapter.estado == ChapterStatus.RENDERIZADO
