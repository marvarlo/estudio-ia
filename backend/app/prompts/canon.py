"""Prompt de generacion de canon -- version condensada de los Pasos 1-6 de
SKILL.md (historias-fantasia), adaptada para pedir un JSON estructurado en
vez de que el LLM escriba directamente el markdown final (canon_writer.py
se encarga de eso despues, de forma deterministica)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StoryBrief:
    estilo_narrativo: str  # ej. "isekai + venganza", "renacimiento/regresion"
    tono: str  # "NORMAL" | "SAFE"
    plataformas: list[str] = field(default_factory=list)
    estilo_visual: str = "anime"
    num_episodios: int = 10
    duracion_objetivo_min: int = 10
    semilla: str = ""  # idea/trama que el usuario ya tiene, o vacio para una original


SYSTEM_PROMPT = """Sos el motor de creacion de historias de un canal de video de fantasia/isekai \
en formato motion comic narrado (imagenes fijas con narracion en off). Generas la biblia de \
continuidad (canon) de UNA temporada completa, en espanol, siguiendo estas reglas:

1. El logline debe tener protagonista + que quiere + que se lo impide, en 1-2 lineas.
2. Las reglas del sistema (magia/poder/sistema de niveles) deben ser EXPLICITAS: como se obtiene \
poder, y sobre todo que es IMPOSIBLE dentro del sistema -- esto evita power creep descontrolado. \
Sin limites duros y no negociables, el canon esta incompleto.
3. El glosario son terminos INVENTADOS propios de esta historia (nombres de artefactos, lugares, \
organizaciones, tecnicas) que se van a repetir palabra por palabra en toda la temporada.
4. El esqueleto de temporada tiene EXACTAMENTE {num_episodios} filas, una por capitulo, cada una \
con un resumen de una linea y su cliffhanger. El cliffhanger del ultimo capitulo debe cerrar el \
arco de temporada (aunque deje gancho de secuela).
5. Nunca generes prosa de capitulos aca -- solo el esqueleto de una linea por capitulo.

Respondé ÚNICAMENTE con un objeto JSON válido (sin explicación antes o después, sin cercas de \
código) con esta forma exacta:
{{
  "logline": "string",
  "premisa": "string (protagonista, que quiere, que se lo impide, en 2-4 oraciones)",
  "reglas_sistema": "string en markdown con sub-parrafos: mecanica central, como se obtiene poder, \
que es imposible (lista con guiones), escenarios de conflicto si aplica",
  "glosario": [{{"termino": "string", "significado": "string", "notas": "string opcional"}}],
  "temporada": [{{"numero": 1, "resumen": "string", "cliffhanger": "string"}}]
}}
"""


def build_canon_prompt(brief: StoryBrief) -> tuple[str, str]:
    system = SYSTEM_PROMPT.format(num_episodios=brief.num_episodios)
    seed_line = (
        f"El usuario ya tiene esta idea/trama, usala como base (podés mejorar ritmo y estructura "
        f"de arco, pero no cambies la premisa central): {brief.semilla}"
        if brief.semilla.strip()
        else "El usuario no tiene una historia todavía -- generá una premisa original acorde al estilo pedido."
    )
    user = (
        f"Estilo narrativo pedido: {brief.estilo_narrativo}.\n"
        f"Tono/rating: {brief.tono}.\n"
        f"Plataforma(s) destino: {', '.join(brief.plataformas) or 'YouTube'}.\n"
        f"Numero de episodios de la temporada: {brief.num_episodios}.\n"
        f"Duracion objetivo por episodio: {brief.duracion_objetivo_min} minutos.\n"
        f"{seed_line}\n\n"
        "Genera el canon completo en el formato JSON pedido."
    )
    return system, user
