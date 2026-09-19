from pathlib import Path

from app.adapters.outbound.storage.story_folder_reader import (
    discover_chapter_numbers,
    read_canon,
    read_chapter_title,
    read_historia_config,
)

CANON_SAMPLE = """# CANON — La Bruja del Espejo

> Biblia de continuidad.

## 1. Logline y premisa

**Protagonista:** Mirel

**Logline (1-2 líneas):**
Cuando su Maestra intenta sacrificarla, una huerfana se convierte en la venganza que nadie vio venir.
"""

PRODUCCION_SAMPLE = "# Capítulo 3 — Sombras en Cristal\n\n| # | Tipo |\n|---|---|\n"


def test_read_canon_extracts_title_and_logline(tmp_path: Path):
    (tmp_path / "canon.md").write_text(CANON_SAMPLE, encoding="utf-8")
    summary = read_canon(tmp_path, fallback_title="fallback")
    assert summary.title == "La Bruja del Espejo"
    assert summary.logline.startswith("Cuando su Maestra intenta sacrificarla")


def test_read_canon_missing_file_uses_fallback(tmp_path: Path):
    summary = read_canon(tmp_path, fallback_title="mi-historia")
    assert summary.title == "mi-historia"
    assert summary.logline == ""


def test_read_historia_config_missing_returns_empty_dict(tmp_path: Path):
    assert read_historia_config(tmp_path) == {}


def test_discover_chapter_numbers_only_counts_dirs_with_produccion(tmp_path: Path):
    (tmp_path / "capitulo-1").mkdir()
    (tmp_path / "capitulo-1" / "produccion.md").write_text("x", encoding="utf-8")
    (tmp_path / "capitulo-2").mkdir()  # sin produccion.md -- no cuenta
    (tmp_path / "capitulo-10").mkdir()
    (tmp_path / "capitulo-10" / "produccion.md").write_text("x", encoding="utf-8")

    assert discover_chapter_numbers(tmp_path) == [1, 10]


def test_read_chapter_title_from_heading(tmp_path: Path):
    produccion_path = tmp_path / "produccion.md"
    produccion_path.write_text(PRODUCCION_SAMPLE, encoding="utf-8")
    assert read_chapter_title(produccion_path, numero=3) == "Sombras en Cristal"


def test_read_chapter_title_missing_file_falls_back_to_number(tmp_path: Path):
    assert read_chapter_title(tmp_path / "no-existe.md", numero=7) == "Capítulo 7"
