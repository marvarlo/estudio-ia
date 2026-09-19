"""Lee la estructura de carpetas que ya usa el skill historias-fantasia
(historia_config.json, canon.md, personajes.json, escenarios.json, voces.json,
capitulo-N/produccion.md) SIN copiar ni mover nada -- el importador apunta a
estos archivos in situ. Ver seccion 10 del doc de arquitectura ('Importacion:
escaneo de una carpeta de historia existente')."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_CHAPTER_DIR_RE = re.compile(r"^capitulo-(\d+)$")
_CHAPTER_TITLE_RE = re.compile(r"^#\s*Cap[ií]tulo\s+\d+\s*[-—:]\s*(.+?)\s*$", re.MULTILINE)
_CANON_TITLE_RE = re.compile(r"^#\s*CANON\s*[-—:]\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_LOGLINE_MARKER_RE = re.compile(r"\*\*Logline[^*]*\*\*:?\s*(.*)$", re.MULTILINE)


def read_json_optional(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_historia_config(root: Path) -> dict:
    return read_json_optional(root / "historia_config.json") or {}


@dataclass
class CanonSummary:
    title: str
    logline: str
    raw_markdown: str


def read_canon(root: Path, fallback_title: str) -> CanonSummary:
    canon_path = root / "canon.md"
    if not canon_path.exists():
        return CanonSummary(title=fallback_title, logline="", raw_markdown="")
    raw = canon_path.read_text(encoding="utf-8")
    title_match = _CANON_TITLE_RE.search(raw)
    title = title_match.group(1).strip() if title_match else fallback_title

    logline = ""
    marker_match = _LOGLINE_MARKER_RE.search(raw)
    if marker_match:
        inline = marker_match.group(1).strip()
        if inline:
            logline = inline
        else:
            # El texto suele ir en la linea SIGUIENTE al marcador en negrita,
            # no en la misma linea -- ver assets/canon_template.md del skill.
            after = raw[marker_match.end():].lstrip("\n")
            next_line = after.split("\n", 1)[0].strip()
            logline = next_line
    return CanonSummary(title=title, logline=logline, raw_markdown=raw)


def discover_chapter_numbers(root: Path) -> list[int]:
    numbers = []
    for path in root.glob("capitulo-*"):
        match = _CHAPTER_DIR_RE.match(path.name)
        if match and (path / "produccion.md").exists():
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def read_chapter_title(produccion_path: Path, numero: int) -> str:
    if not produccion_path.exists():
        return f"Capítulo {numero}"
    raw = produccion_path.read_text(encoding="utf-8")
    match = _CHAPTER_TITLE_RE.search(raw)
    return match.group(1).strip() if match else f"Capítulo {numero}"
