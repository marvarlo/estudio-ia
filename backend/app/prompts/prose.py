"""Prompt de escritura de prosa -- version condensada del Paso 9.1 de
SKILL.md: la prosa manda (es el contenido canonico que despues se ensambla
en el manuscrito), `produccion.md` es una adaptacion suya, nunca al reves."""
from __future__ import annotations

from app.domain.story.entities import Canon, Character, Location, Project, SeasonEpisode

SYSTEM_PROMPT_TEMPLATE = """Sos un novelista escribiendo la prosa completa de UN capitulo de una \
historia de fantasia/isekai en formato motion comic narrado. Te dan el resumen y cliffhanger YA \
APROBADOS de este capitulo especifico (una fila del esqueleto de temporada) -- no improvises un \
rumbo distinto, expandi ESE resumen a una escena completa.

Reglas:
1. Parrafos con descripcion, interioridad de personajes y ritmo narrativo real -- NUNCA una lista \
de lineas sueltas ni un guion tecnico.
2. Respeta la identidad fija de cada personaje/escenario listado cuando aparezca en escena, para \
que la prosa no contradiga su descripcion visual ya establecida.
3. Tono: {tono}. Estilo visual de referencia (para ambientacion, no para prosa): {estilo_visual}.
4. Extension objetivo: aproximadamente {target_words} palabras -- referencia orientativa, no una \
regla rigida; el criterio real es que la escena quede completa y bien resuelta.
5. Empeza con "# Capitulo {numero}: {titulo}" y segui en espanol.

Respondé ÚNICAMENTE con el texto de la prosa (markdown simple, sin JSON, sin cercas de código, sin \
explicaciones antes o después)."""


def _character_block(characters: list[Character]) -> str:
    if not characters:
        return "(sin personajes definidos todavia)"
    lines = []
    for c in characters:
        anchor = c.tokens_visuales.get("descripcion_corta") or c.prompt_anchor or ""
        lines.append(f"- [{c.slug}] {c.nombre} ({c.rol}): {anchor}")
    return "\n".join(lines)


def _location_block(locations: list[Location]) -> str:
    if not locations:
        return "(sin escenarios definidos todavia)"
    return "\n".join(f"- [{l.slug}] {l.nombre}: {l.descripcion_fija}" for l in locations)


def build_prose_prompt(
    project: Project,
    canon: Canon,
    episode: SeasonEpisode,
    characters: list[Character],
    locations: list[Location],
    titulo: str,
    target_words: int,
) -> tuple[str, str]:
    system = SYSTEM_PROMPT_TEMPLATE.format(
        tono=project.tono.value,
        estilo_visual=project.estilo_visual,
        target_words=target_words,
        numero=episode.numero,
        titulo=titulo,
    )
    user = (
        f"Historia: {project.name}\n\n"
        f"Logline: {canon.logline}\n\n"
        f"Reglas del sistema (canon): {canon.reglas_sistema}\n\n"
        f"Resumen del capitulo {episode.numero}: {episode.resumen}\n"
        f"Cliffhanger de cierre: {episode.cliffhanger}\n\n"
        f"Personajes:\n{_character_block(characters)}\n\n"
        f"Escenarios:\n{_location_block(locations)}\n\n"
        f"Escribi la prosa completa del capitulo {episode.numero}."
    )
    return system, user
