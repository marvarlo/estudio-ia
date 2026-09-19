"""Extraccion tolerante de JSON de una respuesta de LLM.

Ni Lemonade (modelos locales chicos) ni Gemini sin `responseMimeType`
garantizan devolver JSON puro -- suelen envolverlo en una cerca de codigo
markdown (```json ... ```) o agregar una frase antes/despues. Esto extrae el
primer objeto/array balanceado del texto en vez de asumir que
`json.loads(texto)` funciona directo.
"""
from __future__ import annotations

import json
import re

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict | list:
    """Lanza json.JSONDecodeError si no encuentra nada parseable -- el
    llamador decide como reportarlo (nunca inventar datos ante un parseo
    fallido)."""
    fence_match = _CODE_FENCE_RE.search(text)
    candidate = fence_match.group(1).strip() if fence_match else text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Sin cerca de codigo (o con texto extra fuera de ella): buscar el primer
    # bloque balanceado { ... } o [ ... ] en el texto completo.
    start_chars = "{["
    end_chars = {"{": "}", "[": "]"}
    for idx, ch in enumerate(candidate):
        if ch in start_chars:
            depth = 0
            for j in range(idx, len(candidate)):
                if candidate[j] == ch:
                    depth += 1
                elif candidate[j] == end_chars[ch]:
                    depth -= 1
                    if depth == 0:
                        block = candidate[idx : j + 1]
                        try:
                            return json.loads(block)
                        except json.JSONDecodeError:
                            break
            break
    # Reintenta el mensaje de error real de json contra el texto completo
    # para que el llamador vea un error util, no uno generico.
    json.loads(candidate)
    raise AssertionError("unreachable")  # json.loads de arriba siempre lanza si llega aca
