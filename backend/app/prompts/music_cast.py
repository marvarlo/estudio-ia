"""Prompt de casting visual para el VIDEOCLIP MUSICAL ANIMADO (fase 5) --
version de cast.py (fase 1) que parte de la letra transcrita de una cancion
en vez de un canon: un elenco breve (tipicamente 1) y un escenario principal
que capturen el mood/tema de la cancion."""
from __future__ import annotations

from dataclasses import dataclass

SYSTEM_PROMPT = """Sos el motor de casting visual de un VIDEOCLIP MUSICAL ANIMADO. A partir de la \
letra transcrita de una cancion, generas un elenco breve (el/la protagonista del videoclip, y a \
veces un segundo personaje si la letra claramente involucra a dos) y UN escenario principal que \
capturen visualmente el mood/tema de la cancion, listos para alimentar un modelo de generacion de \
imagen.

REGLAS PARA CADA PERSONAJE (campos `descripcion_corta`, `cabello`, `ojos`, `marca_distintiva`, \
`atuendo_base`, `prompt_anchor` -- TODOS en INGLES, el resto de la respuesta en espanol):
1. Solo lo que una camara veria. Nunca backstory ni rasgos de personalidad narrativos.
2. Desglosa, no resumas: largo + color + peinado; color + rasgo notable de ojos; el atuendo prenda \
por prenda.
3. `prompt_anchor` es una sola cadena autocontenida en ingles: identidad breve + cabello + ojos + \
atuendo + porte/expresion + 3-5 tags de direccion de arte.
4. `id` es un slug corto en snake_case (ej. protagonista_01).
5. NO inventes un personaje si la letra es puramente abstracta/instrumental sin ningun sujeto \
claro -- en ese caso devolvé la lista de personajes vacia y confia solo en el escenario.
6. NUNCA describas ropa, accesorios u objetos que impliquen texto o logos visibles ("band t-shirt \
with a logo", "graphic tee", "printed slogan", "jersey with a number") -- un generador de imagen \
local casi siempre alucina texto garabateado ilegible al intentar dibujarlos. Describi la prenda \
por su corte/color/textura/material en cambio (ej. "plain black ripped t-shirt", "solid leather \
jacket") -- nunca por lo que dice o representa.

REGLAS PARA EL ESCENARIO (campo `descripcion_fija` en INGLES):
1. Desglose fisico del lugar (arquitectura, materiales, iluminacion, atmosfera) que capture el mood \
general de la cancion -- nunca accion puntual.
2. `id` slug corto en snake_case.

Respondé ÚNICAMENTE con un objeto JSON válido (sin explicación antes o después, sin cercas de \
código) con esta forma exacta:
{
  "personajes": [
    {"id": "string", "nombre": "string", "rol": "protagonista",
     "descripcion_corta": "string en ingles", "cabello": "string en ingles", "ojos": "string en ingles",
     "marca_distintiva": "string en ingles", "atuendo_base": "string en ingles",
     "prompt_anchor": "string en ingles, autocontenido"}
  ],
  "escenarios": [
    {"id": "string", "nombre": "string", "descripcion_fija": "string en ingles"}
  ]
}
"""


@dataclass
class MusicCastBrief:
    estilo_visual: str = "anime"
    notas: str = ""


def build_music_cast_prompt(lyrics_text: str, brief: MusicCastBrief) -> tuple[str, str]:
    notas_line = f"\nNotas adicionales del usuario: {brief.notas}" if brief.notas.strip() else ""
    user = (
        f"Estilo visual: {brief.estilo_visual}\n\n"
        f"Letra transcrita de la cancion:\n{lyrics_text}\n\n"
        f"Genera el elenco y el escenario principal para el videoclip de esta cancion.{notas_line}"
    )
    return SYSTEM_PROMPT, user
