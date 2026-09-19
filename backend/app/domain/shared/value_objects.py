"""Value objects compartidos por todo el dominio.

Estos enums no dependen de ningun framework (FastAPI, SQLModel, Pydantic) a
proposito -- son el vocabulario del negocio, no un detalle de infraestructura.
Los adaptadores (API, DB) los serializan/mapean, nunca al reves.
"""
from __future__ import annotations

from enum import Enum


class ProjectKind(str, Enum):
    """Que clase de producto es un proyecto -- determina que wizard/pasos aplican."""

    STORY = "story"
    MUSIC_VIDEO = "music_video"
    LYRICS_VIDEO = "lyrics_video"
    KARAOKE = "karaoke"


class Tone(str, Enum):
    """Mismo eje NORMAL/SAFE que ya usan las skills historias-fantasia y
    video-clip-creator -- se conserva la convencion, no se reinventa."""

    NORMAL = "NORMAL"
    SAFE = "SAFE"


class ShotType(str, Enum):
    """Tipo de fila/plano. NARRACION y DIALOGO vienen de produccion.md;
    INSTRUMENTAL y LETRA son los tipos nuevos para el pipeline de musica."""

    NARRACION = "Narracion"
    DIALOGO = "Dialogo"
    INSTRUMENTAL = "Instrumental"
    LETRA = "Letra"


class AssetKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SHEET = "sheet"
    STEM = "stem"
    SRT = "srt"


class ChapterStatus(str, Enum):
    BORRADOR = "borrador"
    HOJA_DERIVADA = "hoja_derivada"
    ASSETS = "assets"
    RENDERIZADO = "renderizado"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderCapability(str, Enum):
    """Una capacidad = un puerto de salida. Ver application/ports/ y la
    seccion 4 (Arquitectura hexagonal) del doc de arquitectura."""

    TEXT = "text"
    IMAGE = "image"
    IMAGE_EDIT = "image_edit"
    UPSCALE = "upscale"
    TTS = "tts"
    VOICE_DESIGN = "voice_design"
    VIDEO_I2V = "video_i2v"
    VIDEO_LIPSYNC = "video_lipsync"
    TRANSCRIBE = "transcribe"
    SEPARATE = "separate"
    MUSIC = "music"
    SFX = "sfx"
    TRANSLATE = "translate"
