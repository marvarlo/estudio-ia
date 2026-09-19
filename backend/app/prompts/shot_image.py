"""Construccion del prompt de imagen de un shot -- dos caminos, portados de
scripts/build_full_prompts.py (Lemonade, sin imagenes de referencia) y
scripts/create_images.py (Gemini, multimodal con referencias) del skill
historias-fantasia.

Simplificacion deliberada respecto al script original: Estudio IA guarda
`Shot.personaje_ids` como datos estructurados desde el principio (CRUD de la
fase 1), asi que no hace falta el fallback de deteccion de personajes por
nombre en el texto (`detect_character_ids_from_prompt` en el script
original) que existia porque produccion.md es texto plano -- ac nuestra
fuente de verdad ya es una lista, no texto a interpretar.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.domain.story.entities import Character, Location, Shot

ANTI_TEXT_RULES = (
    "- Absolutely no readable text.\n"
    "- No logos, labels, subtitles, captions, signs, posters, graffiti, watermarks, stickers, or UI elements.\n"
)
ENVIRONMENTAL_TEXT_RULES = (
    "- Environmental/diegetic text IS allowed when it naturally belongs to the physical world of the "
    "scene, as long as it is legible and correctly spelled.\n"
    "- Do NOT add meta-level elements that break the fiction: no logos, watermarks, stickers, UI "
    "elements, captions, or subtitles overlaid on the image.\n"
)
NEGATIVE_PROMPT = (
    "Negative Prompt: deformed anatomy, extra fingers, duplicate limbs, malformed hands, "
    "unwanted extra characters, concept bleeding, inconsistent lighting, bad composition, "
    "text, watermark, low detail, rendering artifacts, cartoonish style, poor lighting, "
    "cluttered composition, chibi."
)
DEFAULT_STYLE_FALLBACK = "anime"

_BRACKET_RE = re.compile(r"\[([a-zA-Z][a-zA-Z0-9_]*)\]")


def substitute_character_id_tokens(text: str, characters_by_slug: dict[str, Character]) -> str:
    def _replace(match: re.Match[str]) -> str:
        character = characters_by_slug.get(match.group(1))
        return character.nombre if character else match.group(0)

    return _BRACKET_RE.sub(_replace, text)


def _character_anchor(character: Character) -> str:
    tokens = character.tokens_visuales
    if tokens.get("prompt_anchor"):
        return tokens["prompt_anchor"]
    partes = [tokens.get("cabello", ""), tokens.get("ojos", ""), tokens.get("marca_distintiva", ""), tokens.get("atuendo_base", "")]
    return f"{character.nombre}, " + ", ".join(p for p in partes if p)


def resolve_scenario_description(location: Location | None, sub_escenario: str) -> str:
    sub_escenario = sub_escenario.strip()
    if location is None:
        return sub_escenario
    if sub_escenario:
        # Un sub-escenario (un cuarto puntual) reemplaza la descripcion
        # general del lugar padre, no se le suma -- mismo criterio que
        # resolve_scenario_description() en build_full_prompts.py.
        return f"{sub_escenario}, inside {location.nombre}"
    return location.descripcion_fija


def format_character_panel(personaje_ids: list[str], characters_by_slug: dict[str, Character]) -> str:
    lines = []
    for slug in personaje_ids:
        character = characters_by_slug.get(slug)
        if character:
            lines.append(f"  - {character.nombre}: {_character_anchor(character)}.")
    return "\n".join(lines)


def build_deterministic_prompt(
    shot: Shot,
    characters_by_slug: dict[str, Character],
    locations_by_slug: dict[str, Location],
    estilo_visual: str,
) -> str:
    """El `full_prompt` para modelos locales sin imagen de referencia
    (Lemonade) -- toda la identidad visual se carga como texto en cada
    llamada, porque el backend no acepta ninguna imagen de referencia."""
    base_prompt = substitute_character_id_tokens(shot.prompt_imagen or shot.texto, characters_by_slug)

    style_line = f"Style: {(estilo_visual or DEFAULT_STYLE_FALLBACK).strip()} style, clean rendering, coherent shading."

    location = locations_by_slug.get(shot.escenario_id) if shot.escenario_id else None
    scenario_desc = resolve_scenario_description(location, shot.sub_escenario)
    background_pieces = [p for p in (scenario_desc, shot.momento_dia.strip()) if p]
    background_line = f"Background: {', '.join(background_pieces)}." if background_pieces else "Background: clean, cinematic environment."

    character_panel = format_character_panel(shot.personaje_ids, characters_by_slug) if shot.personaje_ids else ""

    scene_details = base_prompt
    if len(shot.personaje_ids) >= 2:
        names = [characters_by_slug[pid].nombre for pid in shot.personaje_ids if pid in characters_by_slug]
        scene_details = (
            f"{scene_details} Apply spatial anchoring from left to right across the frame: "
            f"{', next to '.join(names)}; preserve each character's established wardrobe and visual identity"
        )
    scene_line = f"Scene: {scene_details}."

    lines = ["Formatting Rules:", "You MUST format the output strictly following this schema:", style_line, background_line]
    if character_panel:
        lines.extend(["Characters:", character_panel])
    lines.extend([scene_line, NEGATIVE_PROMPT])
    return "\n".join(line for line in lines if line and line.strip())


def build_reference_request(
    shot: Shot,
    characters_by_slug: dict[str, Character],
    locations_by_slug: dict[str, Location],
) -> tuple[str, list[Path], list[str]]:
    """El prompt + referencias para Gemini (multimodal): identidad anclada
    por imagen, el texto solo describe la accion puntual de la fila. Orden:
    fondo primero (si tiene ficha), despues cada personaje en el orden de
    `personaje_ids` (si tiene ficha) -- ver build_multimodal_input() en
    create_images.py. Devuelve (texto_final, rutas_referencia, etiquetas)
    con la MISMA longitud en rutas y etiquetas."""
    scene_text = substitute_character_id_tokens(shot.prompt_imagen or shot.texto, characters_by_slug)

    reference_paths: list[Path] = []
    reference_labels: list[str] = []
    integration_rules: list[str] = []

    location = locations_by_slug.get(shot.escenario_id) if shot.escenario_id else None
    if location and location.reference_image_path:
        index = len(reference_paths) + 1
        reference_paths.append(location.reference_image_path)
        reference_labels.append(
            f"BACKGROUND ENVIRONMENT: the following image (Reference Image {index}) represents the "
            "exact background scene environment."
        )
        integration_rules.append(f"- Place all characters INTO the background environment provided in Reference Image {index}.")

    for slug in shot.personaje_ids:
        character = characters_by_slug.get(slug)
        if not character or not character.reference_image_path:
            continue
        index = len(reference_paths) + 1
        reference_paths.append(character.reference_image_path)
        reference_labels.append(
            f"CHARACTER: the following image (Reference Image {index}) is a character design reference "
            f"sheet for {character.nombre} -- a grid showing multiple angles and expressions of the SAME "
            "person. Use it only to extract this character's identity (face, hairstyle, eye color, "
            "outfit); do not reproduce the grid layout or grey studio background from the sheet itself."
        )

    if reference_paths:
        integration_rules.append(
            "- Preserve the exact facial identity, hairstyle, and clothing of each character from "
            "their respective reference sheet."
        )
        integration_rules.append(
            "- Output a single normal story image -- never a grid, never multiple panels, never the "
            "reference sheet's neutral studio background."
        )
        rules_str = "\n".join(integration_rules)
        final_text = (
            f"SCENE DESCRIPTION:\n{scene_text}\n\n"
            f"COMPOSITION RULES:\n{rules_str}\n\n"
            f"TEXT RULES:\n{ENVIRONMENTAL_TEXT_RULES}"
        )
    else:
        # Sin ninguna referencia disponible todavia (fichas no generadas) --
        # cae a texto plano, igual que create_images.py cuando
        # build_multimodal_input() devuelve None.
        location_desc = resolve_scenario_description(location, shot.sub_escenario)
        final_text = f"{scene_text}. {location_desc}." if location_desc else scene_text

    return final_text, reference_paths, reference_labels
