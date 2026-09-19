"""Prompts de fichas de referencia -- portados de
scripts/create_character_sheets.py del skill historias-fantasia. La ficha de
personaje es un "character turnaround sheet" (8 paneles: 4 poses de cuerpo
completo + 4 expresiones faciales) para darle a un modelo de imagen mucho
mas material de identidad visual que una sola pose incidental -- es la razon
principal por la que la consistencia entre escenas mejora. El recorte
automatico en 8 paneles individuales (`crop_character_panels` en el script
original) queda fuera de la fase 1 -- se genera la ficha completa como
referencia unica, no MO paneles sueltos."""
from __future__ import annotations

from app.domain.story.entities import Character, Location

ANTI_TEXT_RULES = (
    "- Absolutely no readable text.\n"
    "- No logos, labels, subtitles, captions, signs, posters, graffiti, watermarks, stickers, or UI elements.\n"
    "- No English letters, no Japanese characters, no other scripts.\n"
    "- Do not reproduce text from reference images.\n"
    "- The final image must be a pure visual composition with zero typography.\n"
)

ENVIRONMENTAL_TEXT_RULES = (
    "- Environmental/diegetic text IS allowed when it naturally belongs to the physical world of the "
    "scene -- signage, banners, engraved plaques, guild emblems with mottos, book spines, letters, "
    "documents, inscriptions -- as long as it is legible, correctly spelled, and consistent with the "
    "established setting and language.\n"
    "- Do NOT add meta-level elements that break the fiction: no logos, watermarks, stickers, UI "
    "elements, captions, or subtitles overlaid on the image.\n"
    "- If text appears, it must be real and readable -- never garbled, illegible, or nonsensical "
    "pseudo-text.\n"
    "- Text should support the scene, not dominate it -- avoid covering characters or the main visual "
    "focus with large blocks of text.\n"
)


def _character_anchor(character: Character) -> str:
    tokens = character.tokens_visuales
    if tokens.get("prompt_anchor"):
        return tokens["prompt_anchor"]
    partes = [tokens.get("cabello", ""), tokens.get("ojos", ""), tokens.get("marca_distintiva", ""), tokens.get("atuendo_base", "")]
    return ", ".join(p for p in partes if p)


def build_character_sheet_prompt(estilo_visual: str, character: Character) -> str:
    tokens = character.tokens_visuales
    anchor = _character_anchor(character)
    estilo = f"{estilo_visual} style, " if estilo_visual else ""

    if tokens.get("prompt_anchor"):
        character_line = anchor
    else:
        descripcion = tokens.get("descripcion_corta", "")
        character_line = f"{descripcion}. {anchor}" if descripcion else anchor

    return (
        f"{estilo}character reference sheet (model turnaround sheet) for a single character, "
        "on a plain flat neutral grey studio background, clean even studio lighting, no shadows, "
        "no props, no environment, no other characters, no action pose -- this is a character "
        "design reference sheet, not a story scene.\n\n"
        f"CHARACTER: {character_line}.\n\n"
        "LAYOUT: a clean grid with clear spacing between panels --\n"
        "- Top row: four full-body views of the same neutral standing pose (arms relaxed at sides) -- "
        "front view, 3/4 front view, side profile view, back view.\n"
        "- Bottom row: four head-and-shoulders close-ups of the same face -- neutral expression, "
        "warm smiling expression, intense/angry expression, surprised expression.\n\n"
        "CRITICAL CONSISTENCY RULES:\n"
        "- The exact same character must appear identically in all eight panels: identical face, "
        "identical hairstyle and hair color, identical eye color, identical outfit, identical "
        "proportions and body type.\n"
        "- Do not vary the design between panels. This sheet exists specifically to lock down one "
        "consistent design that will be reused as a visual reference in many future images -- "
        "treat it as the single source of truth for this character's appearance.\n\n"
        f"ANTI-TEXT RULES:\n{ANTI_TEXT_RULES}"
    )


def build_location_sheet_prompt(estilo_visual: str, location: Location) -> str:
    """Angulo 1 -- plano general limpio, sin referencia previa (texto solo).
    Los angulos 2+ encadenados con referencia (ver script original) quedan
    fuera de la fase 1."""
    descripcion = location.descripcion_fija
    estilo = f"{estilo_visual} style, " if estilo_visual else ""

    return (
        f"{estilo}a single clean wide establishing shot of a location, empty of any characters, "
        "lit with clear neutral daylight-equivalent lighting so every structural and atmospheric "
        "detail is legible -- this is a background/environment design reference, not a mood-lit "
        "story scene.\n\n"
        f"LOCATION: {descripcion}\n\n"
        "CRITICAL CONSISTENCY RULES:\n"
        "- This image will be reused as a fixed background reference across many future scenes set "
        "at different times of day and with different characters in frame -- keep the composition, "
        "architecture, and layout clear and unambiguous so the location stays recognizable every "
        "time it is reused.\n\n"
        f"TEXT RULES:\n{ENVIRONMENTAL_TEXT_RULES}"
    )
