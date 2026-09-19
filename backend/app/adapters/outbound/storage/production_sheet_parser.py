"""Parser de produccion.md -- puerto de entrada al importador (fase 0).

Porta la logica ya verificada de scripts/build_prompts.py::load_production_sheet
del skill historias-fantasia (mismo formato de tabla pipe-markdown, columnas
opcionales tolerantes a ausencia) y agrega el forward-fill de Escenario/
Sub-Escenario/Momento Dia que build_prompts.py aplica en build_final_rows --
ver references/formato_produccion.md del skill original: 'no hace falta
repetirlo en cada fila, se hereda a las filas siguientes'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_CARRY_FORWARD_COLUMNS = ("escenario", "sub-escenario", "momento dia")
_DURATION_RE = re.compile(r"[\d.]+")


@dataclass
class ParsedShotRow:
    orden: int
    tipo: str
    personaje_ids: list[str] = field(default_factory=list)
    escenario_id: str | None = None
    sub_escenario: str = ""
    momento_dia: str = ""
    texto: str = ""
    prompt_imagen: str = ""
    prompt_video: str = ""
    movimiento_camara: str = ""
    duracion_estimada_seg: float | None = None
    sfx_musica: str = ""


def _parse_pipe_table(text: str) -> list[dict[str, str]]:
    """Extrae filas de la PRIMERA tabla pipe-markdown del texto. Ignora
    cualquier linea que no empiece con '|', la fila de encabezado y la fila
    separadora (---)."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            header = [h.lower() for h in cells]
            continue
        if set(cells[0]) <= {"-", ":"}:
            continue
        # Una tabla nueva (ej. "## Shorts derivados" no es pipe-table, pero
        # por robustez si aparece un header distinto lo tratamos como fin de
        # la tabla de shots).
        row = dict(zip(header, cells))
        rows.append(row)
    return rows


def _parse_duration(raw: str) -> float | None:
    if not raw:
        return None
    match = _DURATION_RE.search(raw)
    return float(match.group()) if match else None


def _split_personajes(raw: str) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def parse_production_sheet(text: str) -> list[ParsedShotRow]:
    raw_rows = _parse_pipe_table(text)
    carry: dict[str, str] = {}
    parsed: list[ParsedShotRow] = []
    for index, raw in enumerate(raw_rows, start=1):
        for column in _CARRY_FORWARD_COLUMNS:
            value = raw.get(column, "").strip()
            if value:
                carry[column] = value
        orden_raw = raw.get("#", "").strip()
        try:
            orden = int(orden_raw)
        except ValueError:
            orden = index
        parsed.append(
            ParsedShotRow(
                orden=orden,
                tipo=raw.get("tipo", "Narracion").strip() or "Narracion",
                personaje_ids=_split_personajes(raw.get("personaje", "")),
                escenario_id=(raw.get("escenario", "").strip() or carry.get("escenario")) or None,
                sub_escenario=raw.get("sub-escenario", "").strip() or carry.get("sub-escenario", ""),
                momento_dia=raw.get("momento dia", "").strip() or carry.get("momento dia", ""),
                texto=raw.get("texto", "").strip(),
                prompt_imagen=raw.get("prompt imagen", "").strip(),
                prompt_video=raw.get("prompt video", "").strip(),
                movimiento_camara=raw.get("movimiento camara", "").strip(),
                duracion_estimada_seg=_parse_duration(raw.get("duracion", "")),
                sfx_musica=raw.get("sfx/musica", "").strip(),
            )
        )
    return parsed


def parse_production_sheet_file(path: Path) -> list[ParsedShotRow]:
    return parse_production_sheet(path.read_text(encoding="utf-8"))
