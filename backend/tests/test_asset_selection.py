import uuid

import pytest

from app.application.use_cases.asset_selection import ListShotAssetsUseCase, SelectShotAssetUseCase
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.shot_editing import CreateShotUseCase, ShotInput
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset


def _make_asset(project_id, chapter_id, shot_id, kind, path) -> Asset:
    return Asset(id=str(uuid.uuid4()), project_id=project_id, chapter_id=chapter_id, shot_id=shot_id, kind=kind, path=path)


def test_list_shot_assets_returns_full_history(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Historial Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="x"))

    first = _make_asset(project.id, chapter.id, shot.id, AssetKind.IMAGE, tmp_path / "v1.png")
    second = _make_asset(project.id, chapter.id, shot.id, AssetKind.IMAGE, tmp_path / "v2.png")
    repository.save_asset(first)
    repository.save_asset(second)

    history = ListShotAssetsUseCase(repository).execute(shot.id)

    assert {a.id for a in history} == {first.id, second.id}


def test_select_asset_switches_selection_without_regenerating(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Seleccion Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="x"))
    older = _make_asset(project.id, chapter.id, shot.id, AssetKind.IMAGE, tmp_path / "v1.png")
    newer = _make_asset(project.id, chapter.id, shot.id, AssetKind.IMAGE, tmp_path / "v2.png")
    repository.save_asset(older)
    repository.save_asset(newer)
    shot.selected_image_asset_id = newer.id
    repository.save_shot(shot)

    updated = SelectShotAssetUseCase(repository).execute(shot.id, older.id)

    assert updated.selected_image_asset_id == older.id


def test_select_asset_from_another_shot_raises(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Cruzado Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    shot_a = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="A"))
    shot_b = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="B"))
    asset_b = _make_asset(project.id, chapter.id, shot_b.id, AssetKind.IMAGE, tmp_path / "b.png")
    repository.save_asset(asset_b)

    with pytest.raises(ValueError, match="no pertenece"):
        SelectShotAssetUseCase(repository).execute(shot_a.id, asset_b.id)


def test_select_unknown_asset_raises(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Inexistente Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="x"))

    with pytest.raises(ValueError, match="Asset no encontrado"):
        SelectShotAssetUseCase(repository).execute(shot.id, "no-existe")
