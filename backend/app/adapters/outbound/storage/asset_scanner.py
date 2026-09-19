"""Escanea los assets ya generados de un capitulo, siguiendo la convencion
documentada en AGENTS.md del skill historias-fantasia (cambio Sep 2026):

    capitulo-N/assets/{width}x{height}/imagenes/capituloN-escenaNN.png
    capitulo-N/assets/{width}x{height}/videos/capituloN-escenaNN.mp4
    capitulo-N/assets/audio/capituloN-escenaNN.mp3   (flat -- el audio no
                                                       tiene orientacion)

No copia archivos: el Asset del dominio guarda la ruta absoluta tal cual
esta en disco. Una carpeta de un capitulo generado ANTES de esta convencion
(assets/imagenes/ plano) queda simplemente sin escanear -- el propio skill
documenta scripts/migrate_assets_formato.py para ese caso, fuera de alcance
de la fase 0.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.domain.shared.value_objects import AssetKind

_FORMATO_RE = re.compile(r"^(\d+)x(\d+)$")
_ESCENA_RE = re.compile(r"escena0*(\d+)", re.IGNORECASE)

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}


@dataclass
class ScannedAsset:
    kind: AssetKind
    path: Path
    shot_orden: int | None
    width: int | None = None
    height: int | None = None


def _extract_shot_number(filename: str) -> int | None:
    match = _ESCENA_RE.search(filename)
    return int(match.group(1)) if match else None


def scan_chapter_assets(chapter_dir: Path) -> list[ScannedAsset]:
    assets_dir = chapter_dir / "assets"
    found: list[ScannedAsset] = []
    if not assets_dir.exists():
        return found

    for formato_dir in assets_dir.iterdir():
        if not formato_dir.is_dir():
            continue
        match = _FORMATO_RE.match(formato_dir.name)
        if not match:
            continue
        width, height = int(match.group(1)), int(match.group(2))

        imagenes_dir = formato_dir / "imagenes"
        if imagenes_dir.is_dir():
            for file_path in sorted(imagenes_dir.iterdir()):
                if file_path.suffix.lower() in _IMAGE_EXTENSIONS:
                    found.append(
                        ScannedAsset(
                            kind=AssetKind.IMAGE,
                            path=file_path,
                            shot_orden=_extract_shot_number(file_path.name),
                            width=width,
                            height=height,
                        )
                    )

        videos_dir = formato_dir / "videos"
        if videos_dir.is_dir():
            for file_path in sorted(videos_dir.iterdir()):
                if file_path.suffix.lower() in _VIDEO_EXTENSIONS:
                    found.append(
                        ScannedAsset(
                            kind=AssetKind.VIDEO,
                            path=file_path,
                            shot_orden=_extract_shot_number(file_path.name),
                            width=width,
                            height=height,
                        )
                    )

    audio_dir = assets_dir / "audio"
    if audio_dir.is_dir():
        for file_path in sorted(audio_dir.iterdir()):
            if file_path.suffix.lower() in _AUDIO_EXTENSIONS:
                found.append(
                    ScannedAsset(
                        kind=AssetKind.AUDIO,
                        path=file_path,
                        shot_orden=_extract_shot_number(file_path.name),
                    )
                )

    return found
