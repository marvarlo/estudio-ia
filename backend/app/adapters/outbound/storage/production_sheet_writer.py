"""Exporta los shots de un capitulo (fuente de verdad: la base de datos,
editada desde la web) de vuelta a produccion.md en el formato exacto de
references/formato_produccion.md del skill original -- para que
build_prompts.py y el resto de la toolchain vieja sigan funcionando sobre un
capitulo editado desde Estudio IA."""
from __future__ import annotations

from pathlib import Path

from app.domain.story.entities import Chapter, Shot

_HEADER = (
    "| # | Tipo | Personaje | Escenario | Sub-Escenario | Momento Dia | Texto | "
    "Prompt Imagen | Prompt Video | Movimiento Camara | Duracion | SFX/Musica |"
)
_SEPARATOR = "|---|---|---|---|---|---|---|---|---|---|---|---|"


def _cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "/").strip()


def render_production_sheet(chapter: Chapter, shots: list[Shot]) -> str:
    lines = [f"# Capítulo {chapter.numero} — {chapter.titulo}", "", _HEADER, _SEPARATOR]
    for shot in shots:
        duracion = f"{shot.duracion_estimada_seg}s" if shot.duracion_estimada_seg is not None else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    str(shot.orden),
                    shot.tipo.value,
                    _cell(", ".join(shot.personaje_ids)),
                    _cell(shot.escenario_id or ""),
                    _cell(shot.sub_escenario),
                    _cell(shot.momento_dia),
                    _cell(shot.texto),
                    _cell(shot.prompt_imagen),
                    _cell(shot.prompt_video),
                    _cell(shot.movimiento_camara),
                    duracion,
                    _cell(shot.sfx_musica),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_production_sheet(path: Path, chapter: Chapter, shots: list[Shot]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_production_sheet(chapter, shots), encoding="utf-8")
