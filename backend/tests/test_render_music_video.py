import uuid
from datetime import datetime, timezone

import pytest

from app.application.ports.media_probe import MediaInfo
from app.application.ports.render import RenderRequest, RenderResult
from app.application.use_cases.music_track import CreateTrackProjectUseCase, GenerateShotsFromLyricsUseCase
from app.application.use_cases.render_music_video import BuildMusicTimelineUseCase, RenderMusicVideoUseCase
from app.domain.music.entities import LyricLine
from app.domain.shared.value_objects import AssetKind, ChapterStatus, ShotType
from app.domain.story.entities import Asset, Shot


class FakeMediaProbe:
    def __init__(self, duration: float = 30.0) -> None:
        self.duration = duration

    def probe(self, path):
        return MediaInfo(duration_seconds=self.duration)


class FakeRenderPort:
    def __init__(self) -> None:
        self.last_request: RenderRequest | None = None

    async def render(self, request: RenderRequest) -> RenderResult:
        self.last_request = request
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"fake-mp4")
        return RenderResult(output_path=request.output_path, duration_seconds=30.0)

    async def concat(self, clips, output_path):  # pragma: no cover
        raise NotImplementedError


def _setup_track_with_shots(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe(30.0)).execute(
        name="Render Music Test", kind="lyrics_video", audio_bytes=b"fake-mp3", audio_filename="song.mp3"
    )
    lines = [
        LyricLine(id="l1", track_id=result.track.id, index=0, text="primera", start=0.0, end=2.0),
        LyricLine(id="l2", track_id=result.track.id, index=1, text="segunda", start=2.0, end=5.0),
    ]
    repository.replace_lyric_lines(result.track.id, lines)
    shots = GenerateShotsFromLyricsUseCase(repository).execute(result.chapter.id, result.track.id)

    assets_dir = result.project.root_path / "capitulo-1" / "assets" / "1280x720" / "imagenes"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for shot in shots:
        img_path = assets_dir / f"{shot.id}.png"
        img_path.write_bytes(b"fake-png")
        asset = Asset(
            id=str(uuid.uuid4()), project_id=result.project.id, chapter_id=result.chapter.id, shot_id=shot.id,
            kind=AssetKind.IMAGE, path=img_path, width=1280, height=720, created_at=datetime.now(timezone.utc),
        )
        repository.save_asset(asset)
        shot.selected_image_asset_id = asset.id
        repository.save_shot(shot)

    return result


def test_build_music_timeline_uses_lyric_timestamps_not_sequential_pauses(tmp_path, repository):
    result = _setup_track_with_shots(tmp_path, repository)

    timeline, public_dir, width, height = BuildMusicTimelineUseCase(repository, FakeMediaProbe(30.0)).execute(
        result.chapter.id, result.track.id
    )

    assert width == 1280 and height == 720
    assert timeline["audio"]["path"] == "audio/track.mp3"
    assert timeline["meta"]["durationInSeconds"] == 30.0
    escenas = timeline["escenas"]
    assert escenas[0]["start"] == 0.0 and escenas[0]["end"] == 2.0
    assert escenas[1]["start"] == 2.0 and escenas[1]["end"] == 5.0
    assert len(timeline["lyrics"]["lines"]) == 2


def test_build_music_timeline_raises_without_background_image(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
        name="No Image Test", kind="karaoke", audio_bytes=b"x", audio_filename="song.mp3"
    )
    lines = [LyricLine(id="l1", track_id=result.track.id, index=0, text="x", start=0.0, end=1.0)]
    repository.replace_lyric_lines(result.track.id, lines)
    GenerateShotsFromLyricsUseCase(repository).execute(result.chapter.id, result.track.id)

    with pytest.raises(ValueError, match="imagen de fondo"):
        BuildMusicTimelineUseCase(repository, FakeMediaProbe()).execute(result.chapter.id, result.track.id)


async def test_render_music_video_creates_video_asset_and_marks_chapter(tmp_path, repository):
    result = _setup_track_with_shots(tmp_path, repository)
    fake_render = FakeRenderPort()

    asset = await RenderMusicVideoUseCase(repository, fake_render, FakeMediaProbe(30.0)).execute(
        result.chapter.id, result.track.id, "LyricsVideo"
    )

    assert asset.kind == AssetKind.VIDEO
    assert asset.shot_id is None
    assert fake_render.last_request.composition_id == "LyricsVideo"
    reloaded_chapter = repository.get_chapter(result.chapter.id)
    assert reloaded_chapter.selected_render_asset_id == asset.id
    assert reloaded_chapter.estado == ChapterStatus.RENDERIZADO


async def test_render_music_video_rejects_unknown_composition(tmp_path, repository):
    result = _setup_track_with_shots(tmp_path, repository)
    with pytest.raises(ValueError, match="composition_id"):
        await RenderMusicVideoUseCase(repository, FakeRenderPort(), FakeMediaProbe()).execute(
            result.chapter.id, result.track.id, "Capitulo"
        )


def test_build_music_timeline_uses_shot_start_seg_not_line_index(tmp_path, repository):
    """Regresion: con MAS shots que lineas de letra (videoclip animado, una
    ventana de beat puede no coincidir 1:1 con una linea), el timeline debia
    seguir usando el tiempo absoluto propio de CADA shot -- antes del fix,
    el codigo reconstruia start/end buscando `lines[i]` por indice, lo que
    con shots ventaneados producia tiempos superpuestos/incorrectos."""
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe(30.0)).execute(
        name="Windowed Test", kind="music_video", audio_bytes=b"x", audio_filename="song.mp3"
    )
    lines = [LyricLine(id="l1", track_id=result.track.id, index=0, text="unica linea", start=0.0, end=2.0)]
    repository.replace_lyric_lines(result.track.id, lines)

    # 3 shots (ventanas), UNA sola linea de letra -- el caso que rompia el
    # indexado por linea.
    shots = [
        Shot(id="s1", chapter_id=result.chapter.id, orden=1, tipo=ShotType.LETRA, start_seg=0.0, duracion_estimada_seg=8.0),
        Shot(id="s2", chapter_id=result.chapter.id, orden=2, tipo=ShotType.INSTRUMENTAL, start_seg=8.0, duracion_estimada_seg=8.0),
        Shot(id="s3", chapter_id=result.chapter.id, orden=3, tipo=ShotType.INSTRUMENTAL, start_seg=16.0, duracion_estimada_seg=8.0),
    ]
    assets_dir = result.project.root_path / "capitulo-1" / "assets" / "1280x720" / "imagenes"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for shot in shots:
        img_path = assets_dir / f"{shot.id}.png"
        img_path.write_bytes(b"fake-png")
        asset = Asset(
            id=str(uuid.uuid4()), project_id=result.project.id, chapter_id=result.chapter.id, shot_id=shot.id,
            kind=AssetKind.IMAGE, path=img_path, width=1280, height=720, created_at=datetime.now(timezone.utc),
        )
        repository.save_asset(asset)
        shot.selected_image_asset_id = asset.id
    repository.replace_shots(result.chapter.id, shots)

    timeline, _public_dir, _w, _h = BuildMusicTimelineUseCase(repository, FakeMediaProbe(30.0)).execute(
        result.chapter.id, result.track.id
    )

    escenas = timeline["escenas"]
    assert [e["start"] for e in escenas] == [0.0, 8.0, 16.0]
    assert [e["end"] for e in escenas] == [8.0, 16.0, 24.0]
    # Sin huecos ni superposiciones entre ventanas consecutivas.
    for a, b in zip(escenas, escenas[1:]):
        assert a["end"] == b["start"]


def test_build_music_timeline_raises_without_start_seg(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe(30.0)).execute(
        name="Missing Start Seg", kind="music_video", audio_bytes=b"x", audio_filename="song.mp3"
    )
    shot = Shot(id="s1", chapter_id=result.chapter.id, orden=1, tipo=ShotType.INSTRUMENTAL, duracion_estimada_seg=8.0)
    assets_dir = result.project.root_path / "capitulo-1" / "assets" / "1280x720" / "imagenes"
    assets_dir.mkdir(parents=True, exist_ok=True)
    img_path = assets_dir / "s1.png"
    img_path.write_bytes(b"fake-png")
    asset = Asset(
        id=str(uuid.uuid4()), project_id=result.project.id, chapter_id=result.chapter.id, shot_id=shot.id,
        kind=AssetKind.IMAGE, path=img_path, width=1280, height=720, created_at=datetime.now(timezone.utc),
    )
    repository.save_asset(asset)
    shot.selected_image_asset_id = asset.id
    repository.replace_shots(result.chapter.id, [shot])

    with pytest.raises(ValueError, match="start_seg"):
        BuildMusicTimelineUseCase(repository, FakeMediaProbe(30.0)).execute(result.chapter.id, result.track.id)
