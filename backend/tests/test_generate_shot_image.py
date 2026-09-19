import base64

import pytest

from app.application.ports.image_generation import ImageGenerationRequest, ImageGenerationResult
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.generate_shot_image import GenerateShotImageUseCase
from app.application.use_cases.shot_editing import CreateShotUseCase, ShotInput
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.story.entities import Character, Location

_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class FakeImagePort:
    def __init__(self) -> None:
        self.last_request: ImageGenerationRequest | None = None

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        self.last_request = request
        return ImageGenerationResult(image_bytes=_TINY_PNG, width=1, height=1, provider="fake", model="fake-model")

    async def health_check(self):  # pragma: no cover
        raise NotImplementedError


def _setup(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Imagenes Test")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Capitulo Uno")
    repository.save_character(
        Character(
            id="char-1", project_id=project.id, slug="protagonista_01", nombre="Vera",
            tokens_visuales={"prompt_anchor": "Vera, warrior, silver hair"},
        )
    )
    repository.save_location(
        Location(id="loc-1", project_id=project.id, slug="templo", nombre="Templo", descripcion_fija="ruined temple")
    )
    shot = CreateShotUseCase(repository).execute(
        chapter.id,
        ShotInput(texto="Vera entra al templo", prompt_imagen="[protagonista_01] entrando al templo", personaje_ids=["protagonista_01"], escenario_id="templo"),
    )
    return project, chapter, shot


async def test_deterministic_prompt_includes_full_visual_identity(tmp_path, repository):
    project, chapter, shot = _setup(tmp_path, repository)
    fake_port = FakeImagePort()

    asset = await GenerateShotImageUseCase(repository, fake_port, supports_references=False).execute(shot.id)

    prompt = fake_port.last_request.prompt
    assert "Style:" in prompt
    assert "warrior, silver hair" in prompt  # el token visual completo, no solo el nombre
    assert "Vera" in prompt  # [protagonista_01] sustituido por el nombre real
    assert fake_port.last_request.reference_images == []  # Lemonade no recibe referencias

    assert asset.path.exists()
    assert asset.width == 1 and asset.height == 1
    reloaded_shot = repository.get_shot(shot.id)
    assert reloaded_shot.selected_image_asset_id == asset.id


async def test_reference_prompt_attaches_character_and_location_sheets(tmp_path, repository):
    project, chapter, shot = _setup(tmp_path, repository)
    # Fichas ya generadas -- deben viajar como referencia.
    character_sheet = tmp_path / "char.png"
    character_sheet.write_bytes(_TINY_PNG)
    location_sheet = tmp_path / "loc.png"
    location_sheet.write_bytes(_TINY_PNG)
    character = repository.get_character_by_slug(project.id, "protagonista_01")
    character.reference_image_path = character_sheet
    repository.save_character(character)
    location = repository.get_location_by_slug(project.id, "templo")
    location.reference_image_path = location_sheet
    repository.save_location(location)

    fake_port = FakeImagePort()
    await GenerateShotImageUseCase(repository, fake_port, supports_references=True).execute(shot.id)

    request = fake_port.last_request
    assert request.reference_images == [location_sheet, character_sheet]
    assert len(request.reference_labels) == 2
    assert "BACKGROUND ENVIRONMENT" in request.reference_labels[0]
    assert "CHARACTER" in request.reference_labels[1]
    assert "SCENE DESCRIPTION" in request.prompt
    # El nombre real, no el token entre corchetes, y sin repetir toda la
    # identidad visual (eso lo aporta la imagen de referencia).
    assert "Vera" in request.prompt
    assert "warrior, silver hair" not in request.prompt


async def test_generate_shot_image_unknown_shot_raises(repository):
    fake_port = FakeImagePort()
    with pytest.raises(ValueError):
        await GenerateShotImageUseCase(repository, fake_port, supports_references=False).execute("no-existe")


async def test_no_select_leaves_shot_selection_untouched(tmp_path, repository):
    project, chapter, shot = _setup(tmp_path, repository)
    fake_port = FakeImagePort()

    await GenerateShotImageUseCase(repository, fake_port, supports_references=False).execute(shot.id, select=False)

    reloaded_shot = repository.get_shot(shot.id)
    assert reloaded_shot.selected_image_asset_id is None
