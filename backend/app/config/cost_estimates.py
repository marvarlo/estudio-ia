"""Estimador de costo aproximado por generacion (seccion 9 del doc de
arquitectura, "mostrar costo estimado antes de cada lote").

Estos numeros son aproximaciones de referencia a partir de precios publicos
tipicos por generacion (no facturacion real verificada, y los proveedores
cambian precios con frecuencia) -- estan pensados para dar una idea de orden
de magnitud antes de lanzar un lote, no como fuente de verdad contable.
Ajustalos libremente en este unico archivo si tenes numeros mas precisos;
nada mas en el codigo depende de que sean exactos.
"""
from __future__ import annotations

# USD aproximados por UNA generacion, sea cual sea el tamano/duracion pedido
# (una simplificacion deliberada -- diferenciar por resolucion/duracion
# exacta añadiría precision falsa sin una fuente de precios verificada).
_ESTIMATES_USD: dict[tuple[str, str], float] = {
    ("lemonade-text", "text"): 0.0,
    ("lemonade-image", "image"): 0.0,
    ("lemonade-tts", "tts"): 0.0,
    ("gemini", "text"): 0.001,
    ("gemini-image", "image"): 0.02,
    ("elevenlabs", "tts"): 0.01,
    ("wan-video", "video"): 0.35,
    ("veo-video", "video"): 0.40,
    ("gemini-omni-video", "video"): 0.30,
}


def estimate_cost(provider_id: str, capability: str) -> float | None:
    return _ESTIMATES_USD.get((provider_id, capability))
