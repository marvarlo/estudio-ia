import base64

from app.application.ports.image_generation import ImageGenerationRequest, ImageGenerationResult
from app.application.use_cases.reference_sheets import (
    GenerateCharacterSheetUseCase,
    GenerateLocationSheetUseCase,
)
from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.domain.story.entities import Character, Location

# PNG 1x1 real y valido (para que png_dimensions() lo pueda parsear de verdad).
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


async def test_generate_character_sheet_writes_file_and_updates_character(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Fichas Test")
    character = Character(
        id="char-1",
        project_id=project.id,
        slug="protagonista_01",
        nombre="Vera",
        tokens_visuales={"prompt_anchor": "Vera, warrior, silver hair"},
    )
    repository.save_character(character)
    fake_port = FakeImagePort()

    asset = await GenerateCharacterSheetUseCase(repository, fake_port).execute(character.id)

    expected_path = project.root_path / "referencias" / "personajes" / "protagonista_01.png"
    assert asset.path == expected_path
    assert expected_path.exists()
    assert asset.width == 1 and asset.height == 1  # leido de verdad de la cabecera PNG
    assert "warrior" in fake_port.last_request.prompt

    updated = repository.get_character(character.id)
    assert updated.reference_image_path == expected_path


async def test_generate_location_sheet_writes_file_and_updates_location(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Fichas Escenario Test")
    location = Location(
        id="loc-1", project_id=project.id, slug="templo_caido", nombre="Templo Caido", descripcion_fija="ruined stone temple"
    )
    repository.save_location(location)
    fake_port = FakeImagePort()

    asset = await GenerateLocationSheetUseCase(repository, fake_port).execute(location.id)

    expected_path = project.root_path / "referencias" / "escenarios" / "templo_caido.png"
    assert expected_path.exists()
    assert "ruined stone temple" in fake_port.last_request.prompt

    updated = repository.get_location(location.id)
    assert updated.reference_image_path == expected_path
