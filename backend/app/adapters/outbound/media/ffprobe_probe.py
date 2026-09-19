"""Implementacion de MediaProbePort via ffprobe -- misma herramienta que ya
usa build_scenes.py del skill original para medir la duracion REAL de cada
audio/video en vez de confiar en el campo `Duracion` estimado a mano."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.application.ports.media_probe import MediaInfo


class FfprobeMediaProbe:
    def probe(self, path: Path) -> MediaInfo:
        try:
            output = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-print_format", "json",
                    "-show_entries", "format=duration:stream=width,height",
                    str(path),
                ],
                capture_output=True, text=True, check=True, timeout=30,
            )
            data = json.loads(output.stdout)
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, OSError):
            return MediaInfo(duration_seconds=None)

        duration = None
        format_info = data.get("format") or {}
        if format_info.get("duration"):
            duration = float(format_info["duration"])

        width = height = None
        for stream in data.get("streams", []):
            if stream.get("width") and stream.get("height"):
                width, height = int(stream["width"]), int(stream["height"])
                break

        return MediaInfo(duration_seconds=duration, width=width, height=height)
