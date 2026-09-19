"""Detecta la extension real de un audio por sus primeros bytes -- hace
falta porque se vio en vivo que Lemonade Server (MOSS-TTS-Local) devuelve
WAV real aunque se pida `Accept: audio/mpeg` (el header no fuerza una
transcodificacion del lado del servidor). Guardar esos bytes con extension
`.mp3` sin verificar producia un archivo con contenido WAV y nombre .mp3 --
funciona por accidente en reproductores tolerantes, pero rompe cualquier
herramienta que valide la extension contra el contenido real (ffprobe con
`-f mp3` explicito, por ejemplo)."""
from __future__ import annotations


def detect_audio_extension(data: bytes, default: str = ".mp3") -> str:
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3"
    if data[:4] == b"OggS":
        return ".ogg"
    return default
