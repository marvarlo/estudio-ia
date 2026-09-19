"""Entidades del dominio de musica (videoclip animado, lyrics video, karaoke).

Fase 0 solo define la forma; el pipeline real (demux, transcripcion,
alineacion) llega en la fase 4 -- ver seccion 6 del doc de arquitectura.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Track:
    id: str
    project_id: str
    source_path: str
    duration_seconds: float | None = None
    bpm: float | None = None
    key: str | None = None
    instrumental_path: str | None = None  # mezcla sin voz, generada por demux


@dataclass
class Stem:
    id: str
    track_id: str
    kind: str  # vocals | drums | bass | other | instrumental
    path: str


@dataclass
class LyricWord:
    text: str
    start: float
    end: float
    confidence: float = 1.0
    suspect: bool = False  # ver transcribe.py -- palabra de baja confianza/duracion implausible


@dataclass
class LyricLine:
    id: str
    track_id: str
    index: int
    text: str
    start: float
    end: float
    words: list[LyricWord] = field(default_factory=list)


@dataclass
class Section:
    id: str
    track_id: str
    kind: str  # intro | verso | coro | puente | solo | outro
    start: float
    end: float
