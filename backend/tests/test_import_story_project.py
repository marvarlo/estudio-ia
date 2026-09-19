import json
from pathlib import Path

from app.application.use_cases.import_story_project import ImportStoryProjectUseCase

PRODUCCION_MD = """# Capítulo 1 — El Comienzo

| # | Tipo | Personaje | Escenario | Momento Dia | Texto | Prompt Imagen | Prompt Video | Movimiento Camara | Duracion | SFX/Musica |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Narracion |  |  | noche | Primera linea de gancho. | un espejo agrietado |  | zoom in lento | 2.8s | musica de tension |
| 2 | Narracion | protagonista_01 | pueblo | amanecer | Segunda linea. | [protagonista_01] caminando |  | pan izquierda | 4.8s |  |
"""


def _write_story_fixture(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "historia_config.json").write_text(
        json.dumps({"historia": "mi-historia-test", "estilo_visual": "anime", "tono": "NORMAL", "plataformas": ["YouTube"]}),
        encoding="utf-8",
    )
    (root / "canon.md").write_text(
        "# CANON — Mi Historia Test\n\n**Logline (1-2 líneas):**\nUna prueba de importacion.\n",
        encoding="utf-8",
    )
    (root / "personajes.json").write_text(
        json.dumps(
            {
                "personajes": [
                    {
                        "id": "protagonista_01",
                        "nombre": "Ana",
                        "rol": "protagonista",
                        "tokens_visuales_fijos": {"prompt_anchor": "Ana, joven, cabello negro"},
                        "referencia_imagen": {"ruta_imagen_referencia": ""},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "escenarios.json").write_text(
        json.dumps(
            {
                "escenarios": [
                    {"id": "pueblo", "nombre": "El pueblo", "descripcion_fija": "small village square"}
                ]
            }
        ),
        encoding="utf-8",
    )
    (root / "voces.json").write_text(
        json.dumps(
            {
                "narrador": {"voz_id_referencia": "narrador-voice-id"},
                "reparto": [{"personaje_id": "protagonista_01", "voz_id_asignada": "ana-voice-id"}],
            }
        ),
        encoding="utf-8",
    )
    chapter_dir = root / "capitulo-1"
    chapter_dir.mkdir()
    (chapter_dir / "produccion.md").write_text(PRODUCCION_MD, encoding="utf-8")

    # Un asset de imagen para la fila 2 (capitulo1-escena02.png), siguiendo
    # la convencion assets/{width}x{height}/imagenes/.
    imagenes_dir = chapter_dir / "assets" / "1280x720" / "imagenes"
    imagenes_dir.mkdir(parents=True)
    (imagenes_dir / "capitulo1-escena02.png").write_bytes(b"fake-png-bytes")


def test_import_creates_project_chapters_shots_and_cast(tmp_path: Path, repository):
    root = tmp_path / "mi-historia-test"
    _write_story_fixture(root)

    summary = ImportStoryProjectUseCase(repository).execute(root)

    assert summary.slug == "mi-historia-test"
    assert summary.name == "Mi Historia Test"
    assert summary.chapters_imported == 1
    assert summary.shots_imported == 2
    assert summary.characters_imported == 1
    assert summary.locations_imported == 1
    assert summary.voices_imported == 2  # narrador + protagonista_01
    assert summary.assets_found == 1
    assert summary.warnings == []

    project = repository.get_project(summary.project_id)
    assert project is not None
    assert project.formatos == ["1280x720"]

    chapters = repository.list_chapters(summary.project_id)
    assert len(chapters) == 1
    assert chapters[0].titulo == "El Comienzo"
    assert chapters[0].estado.value == "assets"  # tiene al menos una imagen

    shots = repository.list_shots(chapters[0].id)
    assert [s.orden for s in shots] == [1, 2]
    assert shots[1].escenario_id == "pueblo"
    assert shots[1].personaje_ids == ["protagonista_01"]

    assets = repository.list_assets(summary.project_id, chapter_id=chapters[0].id)
    assert len(assets) == 1
    assert assets[0].shot_id == shots[1].id  # escena02 -> fila con orden 2

    # El asset importado queda seleccionado por default (fase 2: si no, un
    # shot recien importado se veria como "sin imagen" para el batch).
    reloaded_shot = repository.get_shot(shots[1].id)
    assert reloaded_shot.selected_image_asset_id == assets[0].id

    canon = repository.get_canon(summary.project_id)
    assert canon.logline == "Una prueba de importacion."


def test_reimporting_the_same_folder_is_idempotent(tmp_path: Path, repository):
    root = tmp_path / "mi-historia-test"
    _write_story_fixture(root)

    first = ImportStoryProjectUseCase(repository).execute(root)
    second = ImportStoryProjectUseCase(repository).execute(root)

    assert first.project_id == second.project_id
    assert len(repository.list_projects()) == 1
    assert len(repository.list_chapters(first.project_id)) == 1
    chapter = repository.list_chapters(first.project_id)[0]
    assert len(repository.list_shots(chapter.id)) == 2
    assert len(repository.list_assets(first.project_id, chapter_id=chapter.id)) == 1


def test_missing_folder_raises_file_not_found(repository):
    import pytest

    with pytest.raises(FileNotFoundError):
        ImportStoryProjectUseCase(repository).execute(Path("Z:/no/existe/en/serio"))
