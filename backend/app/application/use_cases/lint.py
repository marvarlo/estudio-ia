"""Linter de la hoja de produccion -- version automatizable de las dos
preguntas del Paso 9.3 de SKILL.md:

1. Un `[personaje_id]` entre corchetes en Prompt Imagen que no esta en la
   columna Personaje de esa fila (esto SI lo puede confirmar un script con
   certeza, portado de build_prompts.py: CHARACTER_ID_TOKEN_RE).
2. Un escenario que cubre una porcion desproporcionada de las filas del
   capitulo (senal de que ahi dentro probablemente hay un lugar mas
   especifico sin su propio id) -- inspirado en scripts/validate_full_prompts.py,
   pero con umbrales elegidos de nuevo para esta fase (no son los valores
   exactos DOMINANT_ESCENARIO_RATIO/MIN_ROWS del script original, que no se
   portaron literalmente).

La segunda pregunta del Paso 9.3 (si un escenario generico esta cubriendo un
lugar mas especifico) es en ultima instancia una lectura de contenido -- este
linter solo da la senal cuantitativa, no reemplaza esa revision.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from app.application.ports.repository import ProjectRepositoryPort

_CHARACTER_ID_TOKEN_RE = re.compile(r"\[([a-zA-Z][a-zA-Z0-9_]*)\]")
DOMINANT_ESCENARIO_RATIO = 0.6
DOMINANT_ESCENARIO_MIN_ROWS = 8


@dataclass
class LintWarning:
    severity: str  # "warning" | "info"
    message: str
    shot_id: str | None = None  # None = advertencia a nivel de capitulo


class LintProductionSheetUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, chapter_id: str) -> list[LintWarning]:
        chapter = self._repository.get_chapter(chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {chapter_id}")
        shots = self._repository.list_shots(chapter_id)
        characters = {c.slug: c for c in self._repository.list_characters(chapter.project_id)}

        warnings: list[LintWarning] = []

        for shot in shots:
            bracket_ids = set(_CHARACTER_ID_TOKEN_RE.findall(shot.prompt_imagen))
            personaje_set = set(shot.personaje_ids)
            for bracket_id in bracket_ids:
                if bracket_id in characters and bracket_id not in personaje_set:
                    warnings.append(
                        LintWarning(
                            severity="warning",
                            shot_id=shot.id,
                            message=(
                                f"[{bracket_id}] aparece en Prompt Imagen pero no esta en la columna "
                                "Personaje de esta fila."
                            ),
                        )
                    )
                elif bracket_id not in characters:
                    warnings.append(
                        LintWarning(
                            severity="info",
                            shot_id=shot.id,
                            message=f"[{bracket_id}] no coincide con ningun personaje conocido de este proyecto.",
                        )
                    )

        escenario_counts = Counter(shot.escenario_id for shot in shots if shot.escenario_id)
        total_con_escenario = sum(escenario_counts.values())
        if total_con_escenario >= DOMINANT_ESCENARIO_MIN_ROWS:
            for escenario_id, count in escenario_counts.items():
                ratio = count / total_con_escenario
                if ratio >= DOMINANT_ESCENARIO_RATIO:
                    warnings.append(
                        LintWarning(
                            severity="info",
                            shot_id=None,
                            message=(
                                f"El escenario '{escenario_id}' cubre {count}/{total_con_escenario} filas "
                                f"({ratio:.0%}) -- revisa si alguna de esas filas describe en realidad un "
                                "lugar mas especifico dentro de el."
                            ),
                        )
                    )

        return warnings
