import json

import pytest

from app.application.ports.text_generation import TextGenerationRequest, TextGenerationResult
from app.application.use_cases.story_generation import (
    CreateStoryProjectUseCase,
    GenerateCanonUseCase,
    GenerateCastUseCase,
)
from app.prompts.canon import StoryBrief
from app.prompts.cast import CastBrief

CANON_JSON = {
    "logline": "Una heroina cansada enfrenta a un dios caido.",
    "premisa": "Premisa de prueba con suficiente detalle.",
    "reglas_sistema": "**Mecanica central:** magia de sangre.\n\n**Que es imposible:**\n- resucitar muertos",
    "glosario": [{"termino": "Sangre Viva", "significado": "energia magica extraida de heridas", "notas": ""}],
    "temporada": [
        {"numero": 1, "resumen": "Arranca el viaje", "cliffhanger": "aparece el dios caido"},
        {"numero": 2, "resumen": "Primer enfrentamiento", "cliffhanger": "la heroina pierde su poder"},
    ],
}

CAST_JSON = {
    "personajes": [
        {
            "id": "protagonista_01",
            "nombre": "Vera",
            "rol": "protagonista",
            "descripcion_corta": "young warrior",
            "cabello": "short silver hair",
            "ojos": "grey eyes",
            "marca_distintiva": "scar on left cheek",
            "atuendo_base": "leather armor",
            "prompt_anchor": "Vera, young warrior, short silver hair, grey eyes, scar on left cheek, leather armor",
        }
    ],
    "escenarios": [{"id": "templo_caido", "nombre": "Templo Caido", "descripcion_fija": "ruined stone temple"}],
}


class FakeTextPort:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.last_request: TextGenerationRequest | None = None

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        self.last_request = request
        return TextGenerationResult(text=self._response_text, model="fake-model", provider="fake")

    async def health_check(self):  # pragma: no cover - no lo usa este caso de uso
        raise NotImplementedError


def test_create_story_project_writes_config_and_persists(tmp_path, repository):
    use_case = CreateStoryProjectUseCase(repository, tmp_path)
    project = use_case.execute(name="Mi Historia de Prueba", estilo_visual="anime", tono="NORMAL")

    assert project.slug == "mi-historia-de-prueba"
    assert project.root_path == tmp_path / "mi-historia-de-prueba"
    config = json.loads((project.root_path / "historia_config.json").read_text(encoding="utf-8"))
    assert config["historia"] == "mi-historia-de-prueba"
    assert repository.get_project(project.id) is not None


def test_create_story_project_dedupes_slug(tmp_path, repository):
    use_case = CreateStoryProjectUseCase(repository, tmp_path)
    first = use_case.execute(name="Duplicada")
    second = use_case.execute(name="Duplicada")
    assert first.slug == "duplicada"
    assert second.slug == "duplicada-2"


@pytest.mark.asyncio
async def test_generate_canon_persists_structured_data_and_writes_markdown(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Canon Test")
    fake_port = FakeTextPort(json.dumps(CANON_JSON))
    brief = StoryBrief(estilo_narrativo="isekai", tono="NORMAL", plataformas=["YouTube"], num_episodios=2)

    canon = await GenerateCanonUseCase(repository, fake_port).execute(project.id, brief)

    assert canon.logline == CANON_JSON["logline"]
    assert len(canon.temporada) == 2
    assert canon.temporada[0].cliffhanger == "aparece el dios caido"
    assert "Sangre Viva" in canon.glosario

    canon_path = project.root_path / "canon.md"
    assert canon_path.exists()
    assert "Canon Test" in canon_path.read_text(encoding="utf-8")

    updated_project = repository.get_project(project.id)
    assert updated_project.num_episodios == 2
    assert fake_port.last_request.json_mode is True


@pytest.mark.asyncio
async def test_generate_canon_raises_value_error_on_bad_json(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Canon Roto")
    fake_port = FakeTextPort("esto no es json en absoluto")
    brief = StoryBrief(estilo_narrativo="isekai", tono="NORMAL")

    with pytest.raises(ValueError, match="JSON valido"):
        await GenerateCanonUseCase(repository, fake_port).execute(project.id, brief)


@pytest.mark.asyncio
async def test_generate_cast_creates_characters_and_locations_with_english_tokens(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Cast Test")
    canon_port = FakeTextPort(json.dumps(CANON_JSON))
    await GenerateCanonUseCase(repository, canon_port).execute(
        project.id, StoryBrief(estilo_narrativo="isekai", tono="NORMAL")
    )

    cast_port = FakeTextPort(json.dumps(CAST_JSON))
    result = await GenerateCastUseCase(repository, cast_port).execute(project.id, CastBrief(num_personajes=1, num_escenarios=1))

    assert len(result.characters) == 1
    character = result.characters[0]
    assert character.slug == "protagonista_01"
    assert character.tokens_visuales["cabello"] == "short silver hair"
    assert character.prompt_anchor.startswith("Vera")

    assert len(result.locations) == 1
    assert result.locations[0].slug == "templo_caido"

    personajes_path = project.root_path / "personajes.json"
    assert personajes_path.exists()
    data = json.loads(personajes_path.read_text(encoding="utf-8"))
    assert data["personajes"][0]["id"] == "protagonista_01"


@pytest.mark.asyncio
async def test_generate_cast_without_canon_raises(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Sin Canon")
    cast_port = FakeTextPort(json.dumps(CAST_JSON))
    with pytest.raises(ValueError, match="canon"):
        await GenerateCastUseCase(repository, cast_port).execute(project.id, CastBrief())
