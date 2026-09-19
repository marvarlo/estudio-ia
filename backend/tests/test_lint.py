import pytest

from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.lint import LintProductionSheetUseCase
from app.application.use_cases.shot_editing import CreateShotUseCase, ShotInput
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.story.entities import Character


def _make_project_and_chapter(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Lint Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    return project, chapter


def test_bracket_character_not_in_personaje_column_warns(tmp_path, repository):
    project, chapter = _make_project_and_chapter(tmp_path, repository)
    repository.save_character(
        Character(id="char-1", project_id=project.id, slug="protagonista_01", nombre="Vera")
    )
    CreateShotUseCase(repository).execute(
        chapter.id,
        ShotInput(texto="x", prompt_imagen="[protagonista_01] caminando", personaje_ids=[]),
    )

    warnings = LintProductionSheetUseCase(repository).execute(chapter.id)

    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "protagonista_01" in warnings[0].message


def test_bracket_character_present_in_personaje_column_is_silent(tmp_path, repository):
    project, chapter = _make_project_and_chapter(tmp_path, repository)
    repository.save_character(
        Character(id="char-1", project_id=project.id, slug="protagonista_01", nombre="Vera")
    )
    CreateShotUseCase(repository).execute(
        chapter.id,
        ShotInput(texto="x", prompt_imagen="[protagonista_01] caminando", personaje_ids=["protagonista_01"]),
    )

    warnings = LintProductionSheetUseCase(repository).execute(chapter.id)

    assert warnings == []


def test_bracket_id_unknown_character_gives_info_not_warning(tmp_path, repository):
    _, chapter = _make_project_and_chapter(tmp_path, repository)
    CreateShotUseCase(repository).execute(
        chapter.id, ShotInput(texto="x", prompt_imagen="[fantasma_01] aparece")
    )

    warnings = LintProductionSheetUseCase(repository).execute(chapter.id)

    assert len(warnings) == 1
    assert warnings[0].severity == "info"


def test_dominant_escenario_flagged_at_chapter_level(tmp_path, repository):
    _, chapter = _make_project_and_chapter(tmp_path, repository)
    create = CreateShotUseCase(repository)
    for _ in range(8):
        create.execute(chapter.id, ShotInput(texto="x", escenario_id="salon_generico"))
    create.execute(chapter.id, ShotInput(texto="x", escenario_id="cuarto_especifico"))

    warnings = LintProductionSheetUseCase(repository).execute(chapter.id)

    chapter_level = [w for w in warnings if w.shot_id is None]
    assert len(chapter_level) == 1
    assert "salon_generico" in chapter_level[0].message


def test_no_dominant_escenario_below_min_rows(tmp_path, repository):
    _, chapter = _make_project_and_chapter(tmp_path, repository)
    create = CreateShotUseCase(repository)
    for _ in range(3):
        create.execute(chapter.id, ShotInput(texto="x", escenario_id="salon_generico"))

    warnings = LintProductionSheetUseCase(repository).execute(chapter.id)

    assert warnings == []


def test_lint_unknown_chapter_raises(repository):
    with pytest.raises(ValueError):
        LintProductionSheetUseCase(repository).execute("no-existe")
