import pytest

from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.shot_editing import (
    CreateShotUseCase,
    DeleteShotUseCase,
    ReorderShotsUseCase,
    ShotInput,
    UpdateShotUseCase,
)
from app.application.use_cases.story_generation import CreateStoryProjectUseCase


def _make_chapter(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Shots Test")
    return CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")


def test_create_shot_assigns_sequential_orden(tmp_path, repository):
    chapter = _make_chapter(tmp_path, repository)
    use_case = CreateShotUseCase(repository)

    first = use_case.execute(chapter.id, ShotInput(texto="Primera fila"))
    second = use_case.execute(chapter.id, ShotInput(texto="Segunda fila"))

    assert first.orden == 1
    assert second.orden == 2
    assert repository.list_shots(chapter.id) == [first, second]


def test_update_shot_changes_fields(tmp_path, repository):
    chapter = _make_chapter(tmp_path, repository)
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="Original"))

    updated = UpdateShotUseCase(repository).execute(
        shot.id, ShotInput(tipo="Dialogo", texto="Editado", personaje_ids=["protagonista_01"])
    )

    assert updated.tipo.value == "Dialogo"
    assert updated.texto == "Editado"
    assert updated.personaje_ids == ["protagonista_01"]
    assert updated.orden == shot.orden  # el orden no cambia al editar contenido


def test_update_unknown_shot_raises(repository):
    with pytest.raises(ValueError):
        UpdateShotUseCase(repository).execute("no-existe", ShotInput())


def test_delete_shot_removes_it(tmp_path, repository):
    chapter = _make_chapter(tmp_path, repository)
    shot = CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="Para borrar"))

    DeleteShotUseCase(repository).execute(shot.id)

    assert repository.get_shot(shot.id) is None


def test_reorder_shots_reassigns_orden_sequentially(tmp_path, repository):
    chapter = _make_chapter(tmp_path, repository)
    use_case = CreateShotUseCase(repository)
    a = use_case.execute(chapter.id, ShotInput(texto="A"))
    b = use_case.execute(chapter.id, ShotInput(texto="B"))
    c = use_case.execute(chapter.id, ShotInput(texto="C"))

    reordered = ReorderShotsUseCase(repository).execute(chapter.id, [c.id, a.id, b.id])

    assert [s.texto for s in reordered] == ["C", "A", "B"]
    assert [s.orden for s in reordered] == [1, 2, 3]


def test_reorder_rejects_incomplete_list(tmp_path, repository):
    chapter = _make_chapter(tmp_path, repository)
    use_case = CreateShotUseCase(repository)
    a = use_case.execute(chapter.id, ShotInput(texto="A"))
    use_case.execute(chapter.id, ShotInput(texto="B"))

    with pytest.raises(ValueError):
        ReorderShotsUseCase(repository).execute(chapter.id, [a.id])


def test_reorder_rejects_unknown_id(tmp_path, repository):
    chapter = _make_chapter(tmp_path, repository)
    CreateShotUseCase(repository).execute(chapter.id, ShotInput(texto="A"))

    with pytest.raises(ValueError):
        ReorderShotsUseCase(repository).execute(chapter.id, ["id-inventado"])
