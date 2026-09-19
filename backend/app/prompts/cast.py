"""Prompt de generacion de cast -- version condensada del Paso 7 de
SKILL.md: personajes y escenarios recurrentes, con tokens visuales pensados
para alimentar directo un modelo de imagen (en ingles, solo lo que una
camara veria, desglosado prenda por prenda en vez de resumido)."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.story.entities import Canon, Project

SYSTEM_PROMPT = """Sos el motor de casting visual de una historia de fantasia/isekai en formato \
motion comic narrado. A partir del canon ya aprobado, generas el elenco de personajes principales/\
secundarios y los escenarios recurrentes, listos para alimentar un modelo de generacion de imagen.

REGLAS PARA CADA PERSONAJE (campos `descripcion_corta`, `cabello`, `ojos`, `marca_distintiva`, \
`atuendo_base`, `prompt_anchor` -- TODOS en INGLES, el resto de la respuesta en espanol):
1. Solo lo que una camara veria. Nunca relacion con otros personajes, reputacion, backstory ni \
rasgos de personalidad narrativos -- eso vive en el canon, no en un prompt de imagen.
2. Desglosa, no resumas: largo + color + peinado + como cae el cabello; color + rasgo notable de \
ojos; el atuendo prenda por prenda (base, capa exterior, cinturon, calzado, accesorios).
3. `prompt_anchor` es una sola cadena autocontenida en ingles: nombre + identidad breve + cabello + \
ojos + atuendo prenda por prenda + porte/expresion + 3-5 tags de direccion de arte (ej. "clean \
linework, soft shading, natural proportions, coherent anatomy, cinematic composition").
4. `id` es un slug corto en snake_case por rol (ej. protagonista_01, antagonista_01, \
secundario_01) -- se va a usar tal cual en produccion.md y en los prompts de imagen.

REGLAS PARA CADA ESCENARIO (campo `descripcion_fija` en INGLES):
1. Solo escenarios que se van a repetir varias veces en la temporada -- no lugares de una sola \
aparicion.
2. Desglose fisico del lugar (arquitectura, materiales, iluminacion, atmosfera), nunca quien lo \
habita o que pasa ahi.
3. `id` slug corto en snake_case (ej. torre_ysolda, pueblo_miralda).

Respondé ÚNICAMENTE con un objeto JSON válido (sin explicación antes o después, sin cercas de \
código) con esta forma exacta:
{
  "personajes": [
    {"id": "string", "nombre": "string", "rol": "protagonista|antagonista|secundario",
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
class CastBrief:
    num_personajes: int = 5
    num_escenarios: int = 4
    notas: str = ""  # pedido libre adicional del usuario, opcional


def build_cast_prompt(project: Project, canon: Canon, brief: CastBrief) -> tuple[str, str]:
    notas_line = f"\nNotas adicionales del usuario: {brief.notas}" if brief.notas.strip() else ""
    user = (
        f"Historia: {project.name}. Estilo visual: {project.estilo_visual}.\n\n"
        f"Logline: {canon.logline}\n\n"
        f"Premisa: {canon.premisa}\n\n"
        f"Reglas del sistema:\n{canon.reglas_sistema}\n\n"
        f"Esqueleto de temporada:\n"
        + "\n".join(f"- Cap. {ep.numero}: {ep.resumen}" for ep in canon.temporada)
        + f"\n\nGenera {brief.num_personajes} personajes principales/secundarios y "
        f"{brief.num_escenarios} escenarios recurrentes.{notas_line}"
    )
    return SYSTEM_PROMPT, user
