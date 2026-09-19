"""Prompt de derivacion de produccion.md desde la prosa -- version condensada
del Paso 9.2 de SKILL.md. Simplificaciones deliberadas respecto al original
(documentadas, no silenciosas -- ver README): el modelo elige entre los
personajes/escenarios YA EXISTENTES en vez de poder crear escenarios nuevos
sobre la marcha (eso requeriria generarles tambien una descripcion_fija
digna de una ficha de referencia, fuera de alcance de este paso), y cada
fila sale con sus campos totalmente resueltos -- Estudio IA no implementa
la herencia fila-a-fila de Escenario/Momento Dia que si hacia
build_full_prompts.py, porque el modelo de datos ya persiste cada Shot con
sus campos explicitos (no hay un paso de parseo posterior que herede nada)."""
from __future__ import annotations

from app.domain.story.entities import Character, Location, Project

# Mismo vocabulario que parseCameraMove() en render/src/camera.ts -- una
# directiva fuera de esta lista cae al Ken Burns generico por defecto ahi,
# asi que no tiene sentido que el modelo invente otras.
CAMERA_VOCAB = (
    "estatico, zoom in, zoom out, pan izquierda, pan derecha "
    "(cada una opcionalmente con lento/rapido/muy rapido, ej. \"zoom in lento\", \"pan derecha rapido\")"
)

SYSTEM_PROMPT = """Sos el motor de derivacion de hoja de produccion de un capitulo de motion comic \
narrado. A partir de la PROSA ya escrita de un capitulo (el contenido canonico), la convertis en \
una tabla de shots (una fila por escena/cambio de locacion/intercambio de dialogo relevante) lista \
para generar imagen/audio/video.

REGLAS:
1. `texto` NO es una copia literal de la prosa -- la prosa esta escrita para leerse, `texto` esta \
para escucharse (frases cortas, ritmo hablado). Adapta cada pasaje, no lo pegues tal cual.
2. `personaje_ids`: SOLO ids de la lista de personajes dada (nunca inventes uno nuevo). En una fila \
de dialogo, el primer id es siempre el que habla. Si otro personaje esta presente en el plano sin \
hablar, agregalo despues. Vacio si la fila no tiene a nadie en camara a proposito (paisaje, objeto).
3. `escenario_id`: SOLO un id de la lista de escenarios dada, o null si ninguno aplica -- nunca \
inventes uno nuevo.
4. `prompt_imagen` (en INGLES): nombra a cada personaje presente con su id entre corchetes \
(`[id_del_personaje]`), NUNCA su nombre real ni un generico ("him", "her", "both") -- un parser \
downstream reemplaza cada `[id]` por el anchor visual real. Todo `[id]` que uses en `prompt_imagen` \
tiene que estar tambien en `personaje_ids`. Describe la accion/composicion de ESA fila puntual, sin \
repetir la identidad fisica del personaje (eso lo inyecta el parser aparte).
5. `movimiento_camara`: SOLO una de estas directivas en espanol: """ + CAMERA_VOCAB + """.
6. `duracion_estimada_seg`: estimacion realista a ritmo hablado (~2.3-2.6 palabras/seg en espanol) \
segun cuanto texto tiene esa fila.
7. Audio tags tipo `[whispers]`, `[sighs]`, `[frustrated]` (en ingles, entre corchetes DENTRO de \
`texto`) solo en los momentos de mayor peso emocional (revelaciones, confrontaciones, quiebres) -- \
nunca en cada fila.
8. `tipo` es `Narracion` o `Dialogo`.

Respondé ÚNICAMENTE con un objeto JSON válido (sin explicación antes o después, sin cercas de \
código) con esta forma exacta:
{
  "shots": [
    {"tipo": "Narracion|Dialogo", "personaje_ids": ["id1"], "escenario_id": "id_o_null",
     "sub_escenario": "string libre o vacio", "momento_dia": "string libre o vacio",
     "texto": "string en espanol", "prompt_imagen": "string en ingles con [id] entre corchetes",
     "prompt_video": "string en ingles o vacio", "movimiento_camara": "string",
     "duracion_estimada_seg": 0.0, "sfx_musica": "string o vacio"}
  ]
}
"""


def _character_block(characters: list[Character]) -> str:
    if not characters:
        return "(sin personajes -- deja personaje_ids vacio en todas las filas)"
    return "\n".join(f"- {c.slug}: {c.nombre} ({c.rol})" for c in characters)


def _location_block(locations: list[Location]) -> str:
    if not locations:
        return "(sin escenarios -- deja escenario_id en null en todas las filas)"
    return "\n".join(f"- {l.slug}: {l.nombre}" for l in locations)


def build_production_sheet_prompt(
    project: Project, prosa: str, characters: list[Character], locations: list[Location]
) -> tuple[str, str]:
    user = (
        f"Estilo visual: {project.estilo_visual}\n\n"
        f"Personajes disponibles:\n{_character_block(characters)}\n\n"
        f"Escenarios disponibles:\n{_location_block(locations)}\n\n"
        f"Prosa del capitulo:\n{prosa}\n\n"
        "Deriva la hoja de produccion completa de este capitulo."
    )
    return SYSTEM_PROMPT, user
