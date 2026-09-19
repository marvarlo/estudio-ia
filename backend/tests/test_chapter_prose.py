import json

import pytest

from app.application.ports.text_generation import TextGenerationRequest, TextGenerationResult
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.chapter_prose import DeriveProductionSheetFromProseUseCase, WriteChapterProseUseCase
from app.application.use_cases.story_generation import CreateStoryProjectUseCase, GenerateCanonUseCase, GenerateCastUseCase
from app.domain.shared.value_objects import ChapterStatus, ShotType
from app.prompts.canon import StoryBrief
from app.prompts.cast import CastBrief

CANON_JSON = {
    "logline": "Una heroina cansada enfrenta a un dios caido.",
    "premisa": "Premisa de prueba.",
    "reglas_sistema": "Magia de sangre.",
    "glosario": [],
    "temporada": [
        {"numero": 1, "resumen": "Arranca el viaje", "cliffhanger": "aparece el dios caido"},
        {"numero": 2, "resumen": "Primer enfrentamiento", "cliffhanger": "pierde su poder"},
    ],
}

CAST_JSON = {
    "personajes": [
        {"id": "protagonista_01", "nombre": "Vera", "rol": "protagonista", "descripcion_corta": "young warrior"},
    ],
    "escenarios": [{"id": "templo_caido", "nombre": "Templo Caido", "descripcion_fija": "ruined stone temple"}],
}

PRODUCTION_SHEET_JSON = {
    "shots": [
        {
            "tipo": "Narracion",
            "personaje_ids": [],
            "escenario_id": "templo_caido",
            "sub_escenario": "",
            "momento_dia": "atardecer",
            "texto": "El templo se alzaba en silencio.",
            "prompt_imagen": "Ruined temple at dusk, wide establishing shot.",
            "prompt_video": "",
            "movimiento_camara": "zoom in lento",
            "duracion_estimada_seg": 3.5,
            "sfx_musica": "",
        },
        {
            "tipo": "Dialogo",
            "personaje_ids": ["protagonista_01"],
            "escenario_id": "templo_caido",
            "sub_escenario": "",
            "momento_dia": "",
            "texto": "No voy a retroceder.",
            "prompt_imagen": "Close up of [protagonista_01] standing defiant.",
            "prompt_video": "",
            "movimiento_camara": "estatico",
            "duracion_estimada_seg": 2.0,
            "sfx_musica": "",
        },
        {
            "tipo": "Dialogo",
            "personaje_ids": ["personaje_inventado"],
            "escenario_id": "lugar_inventado",
            "sub_escenario": "",
            "momento_dia": "",
            "texto": "Fila con ids que no existen.",
            "prompt_imagen": "x",
            "prompt_video": "",
            "movimiento_camara": "pan derecha",
            "duracion_estimada_seg": 1.0,
            "sfx_musica": "",
        },
    ]
}


class FakeTextPort:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.last_request: TextGenerationRequest | None = None

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        self.last_request = request
        return TextGenerationResult(text=self._response_text, model="fake-model", provider="fake")

    async def health_check(self):  # pragma: no cover
        raise NotImplementedError


async def _setup_project_with_canon_and_cast(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Historia De Prueba")
    canon = await GenerateCanonUseCase(repository, FakeTextPort(json.dumps(CANON_JSON))).execute(
        project.id,
        StoryBrief(estilo_narrativo="epico", tono="NORMAL", plataformas=["YouTube"], estilo_visual="anime",
                   num_episodios=2, duracion_objetivo_min=10, semilla=""),
    )
    await GenerateCastUseCase(repository, FakeTextPort(json.dumps(CAST_JSON))).execute(
        project.id, CastBrief(num_personajes=1, num_escenarios=1, notas="")
    )
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="El Comienzo", numero=1)
    return project, canon, chapter


async def test_write_chapter_prose_writes_file_and_sets_prosa_path(tmp_path, repository):
    project, canon, chapter = await _setup_project_with_canon_and_cast(tmp_path, repository)
    fake_port = FakeTextPort("# Capitulo 1: El Comienzo\n\nHabia una vez un templo caido...")

    updated = await WriteChapterProseUseCase(repository, fake_port).execute(chapter.id)

    assert updated.prosa_path is not None
    assert updated.prosa_path.exists()
    assert "templo caido" in updated.prosa_path.read_text(encoding="utf-8")
    assert fake_port.last_request.json_mode is False
    assert "Arranca el viaje" in fake_port.last_request.prompt

    reloaded = repository.get_chapter(chapter.id)
    assert reloaded.prosa_path == updated.prosa_path


async def test_write_chapter_prose_raises_without_canon(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Sin Canon")
    chapter = CreateChapterUseCase(repository).execute(project.id, titulo="Cap 1", numero=1)

    with pytest.raises(ValueError, match="canon"):
        await WriteChapterProseUseCase(repository, FakeTextPort("x")).execute(chapter.id)


async def test_write_chapter_prose_raises_without_season_skeleton_row(tmp_path, repository):
    project, canon, chapter = await _setup_project_with_canon_and_cast(tmp_path, repository)
    # Capitulo 5 no tiene fila en el esqueleto de 2 episodios generado arriba.
    chapter5 = CreateChapterUseCase(repository).execute(project.id, titulo="Cap 5", numero=5)

    with pytest.raises(ValueError, match="esqueleto"):
        await WriteChapterProseUseCase(repository, FakeTextPort("x")).execute(chapter5.id)


async def test_derive_production_sheet_creates_shots_filtering_unknown_ids(tmp_path, repository):
    project, canon, chapter = await _setup_project_with_canon_and_cast(tmp_path, repository)
    await WriteChapterProseUseCase(repository, FakeTextPort("# Capitulo 1\n\nProsa de prueba.")).execute(chapter.id)

    shots = await DeriveProductionSheetFromProseUseCase(repository, FakeTextPort(json.dumps(PRODUCTION_SHEET_JSON))).execute(
        chapter.id
    )

    assert len(shots) == 3
    assert shots[0].tipo == ShotType.NARRACION
    assert shots[0].escenario_id == "templo_caido"
    assert shots[1].tipo == ShotType.DIALOGO
    assert shots[1].personaje_ids == ["protagonista_01"]
    # Fila 3 referenciaba ids inventados -- se descartan en vez de inventar personajes/escenarios.
    assert shots[2].personaje_ids == []
    assert shots[2].escenario_id is None

    reloaded_chapter = repository.get_chapter(chapter.id)
    assert reloaded_chapter.estado == ChapterStatus.HOJA_DERIVADA
    reloaded_shots = repository.list_shots(chapter.id)
    assert len(reloaded_shots) == 3


async def test_derive_production_sheet_raises_without_prose(tmp_path, repository):
    project, canon, chapter = await _setup_project_with_canon_and_cast(tmp_path, repository)

    with pytest.raises(ValueError, match="prosa"):
        await DeriveProductionSheetFromProseUseCase(repository, FakeTextPort("{}")).execute(chapter.id)


async def test_derive_production_sheet_raises_on_invalid_json(tmp_path, repository):
    project, canon, chapter = await _setup_project_with_canon_and_cast(tmp_path, repository)
    await WriteChapterProseUseCase(repository, FakeTextPort("# Capitulo 1\n\nProsa.")).execute(chapter.id)

    with pytest.raises(ValueError, match="JSON"):
        await DeriveProductionSheetFromProseUseCase(repository, FakeTextPort("esto no es json")).execute(chapter.id)
