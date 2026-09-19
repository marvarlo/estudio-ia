import uuid
from datetime import datetime, timezone

import pytest

from app.application.ports.media_probe import MediaInfo
from app.application.ports.render import RenderRequest, RenderResult
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.render_season import RenderSeasonUseCase
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.shared.value_objects import AssetKind, ChapterStatus
from app.domain.story.entities import Asset


class FakeMediaProbe:
    def probe(self, path):
        return MediaInfo(duration_seconds=10.0)


class FakeRenderPort:
    def __init__(self) -> None:
        self.render_calls: list[RenderRequest] = []
        self.concat_calls: list[tuple[list, object]] = []

    async def render(self, request: RenderRequest) -> RenderResult:
        self.render_calls.append(request)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"fake-mp4")
        return RenderResult(output_path=request.output_path, duration_seconds=3.0)

    async def concat(self, clips, output_path) -> RenderResult:
        self.concat_calls.append((clips, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-final-mp4")
        return RenderResult(output_path=output_path, duration_seconds=30.0)


def _make_rendered_chapter(tmp_path, repository, project, numero, titulo):
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo=titulo, numero=numero)
    video_path = project.root_path / f"capitulo-{numero}" / "assets" / "render" / "out.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"fake-chapter-mp4")
    asset = Asset(
        id=str(uuid.uuid4()), project_id=project.id, chapter_id=chapter.id, shot_id=None,
        kind=AssetKind.VIDEO, path=video_path, created_at=datetime.now(timezone.utc),
    )
    repository.save_asset(asset)
    chapter.selected_render_asset_id = asset.id
    chapter.estado = ChapterStatus.RENDERIZADO
    repository.save_chapter(chapter)
    return chapter, asset


async def test_render_season_concats_chapters_with_separators_and_cierre(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Temporada Test")
    _c1, asset1 = _make_rendered_chapter(tmp_path, repository, project, 1, "El Comienzo")
    _c2, asset2 = _make_rendered_chapter(tmp_path, repository, project, 2, "La Caida")
    fake_render = FakeRenderPort()

    final_asset = await RenderSeasonUseCase(repository, fake_render, FakeMediaProbe()).execute(project.id)

    assert final_asset.kind == AssetKind.VIDEO
    assert final_asset.chapter_id is None
    # Un separador (antes del capitulo 2) + un cierre = 2 llamadas a render().
    assert len(fake_render.render_calls) == 2
    assert fake_render.render_calls[0].composition_id == "Separador"
    assert fake_render.render_calls[0].timeline["numeroCapitulo"] == 2
    assert fake_render.render_calls[1].composition_id == "Cierre"
    # El orden del concat: capitulo1, separador, capitulo2, cierre.
    clips, _output = fake_render.concat_calls[0]
    assert clips[0] == asset1.path
    assert clips[2] == asset2.path

    reloaded_project = repository.get_project(project.id)
    assert reloaded_project.selected_season_asset_id == final_asset.id


async def test_render_season_raises_without_chapters(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Vacia")
    with pytest.raises(ValueError, match="capitulos"):
        await RenderSeasonUseCase(repository, FakeRenderPort(), FakeMediaProbe()).execute(project.id)


async def test_render_season_raises_when_chapter_not_rendered(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Incompleta")
    CreateChapterUseCase(repository).execute(project.id, titulo="Cap 1", numero=1)

    with pytest.raises(ValueError, match="todavia no fue renderizado"):
        await RenderSeasonUseCase(repository, FakeRenderPort(), FakeMediaProbe()).execute(project.id)
