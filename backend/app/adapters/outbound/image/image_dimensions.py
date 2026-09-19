"""Lee ancho/alto reales de un PNG por su cabecera IHDR, sin depender de
Pillow -- misma idea que `image_dimensions()` en create_images.py del skill
original: la carpeta/registro se nombra segun la resolucion REAL devuelta
por el proveedor, nunca segun lo pedido (`--aspect-ratio`), porque un
proveedor no siempre respeta el tamano exacto solicitado."""
from __future__ import annotations

import struct


def png_dimensions(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("No es un PNG valido (o le falta la cabecera IHDR)")
    width, height = struct.unpack(">II", data[16:24])
    return width, height
