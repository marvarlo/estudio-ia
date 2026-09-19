"""Adaptador de separacion de fuentes via Demucs (`htdemucs_6s`), invocado
como subproceso -- igual que RemotionRenderAdapter, PyTorch/Demucs viven en
un ejecutable/venv aparte del backend (`demucs` pesa varios GB con PyTorch,
seccion 6 del doc de arquitectura: "instalar en un venv aparte por el peso
de PyTorch") en vez de una dependencia del proyecto principal.

NO verificado en vivo en esta maquina (sin GPU NVIDIA y sin Demucs/PyTorch
instalados aqui, ver memoria del entorno) -- implementado y cubierto por
tests de contrato, mismo criterio que los adaptadores cloud de la fase 2 sin
credenciales disponibles. `demucs_command` es configurable para apuntar al
interprete de ese venv aparte cuando exista."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from app.application.ports.source_separation import SeparationResult

# Salida de `demucs -n htdemucs_6s <audio>` (por defecto model de 6 stems):
# <outdir>/htdemucs_6s/<nombre-sin-extension>/{vocals,drums,bass,guitar,piano,other}.wav
_STEM_NAMES = ("vocals", "drums", "bass", "guitar", "piano", "other")


class DemucsSeparationAdapter:
    def __init__(self, output_root: Path, demucs_command: str = "demucs", model: str = "htdemucs_6s") -> None:
        self._output_root = output_root
        self._demucs_command = demucs_command
        self._model = model

    async def separate(self, audio_path: Path) -> SeparationResult:
        command = shutil.which(self._demucs_command) or self._demucs_command
        out_dir = self._output_root / audio_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        proc = await asyncio.create_subprocess_exec(
            command, "-n", self._model, "-o", str(out_dir), str(audio_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Demucs fallo al separar '{audio_path}' (exit {proc.returncode}):\n{stderr.decode(errors='replace')}")

        stems_dir = out_dir / self._model / audio_path.stem
        stems: dict[str, Path] = {}
        for name in _STEM_NAMES:
            stem_path = stems_dir / f"{name}.wav"
            if stem_path.exists():
                stems[name] = stem_path

        instrumental_path = await self._mix_instrumental(stems_dir, stems)
        if instrumental_path is not None:
            stems["instrumental"] = instrumental_path

        return SeparationResult(stems=stems)

    async def _mix_instrumental(self, stems_dir: Path, stems: dict[str, Path]) -> Path | None:
        non_vocal = [path for name, path in stems.items() if name != "vocals"]
        if not non_vocal:
            return None
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            return None
        output_path = stems_dir / "instrumental.wav"
        inputs: list[str] = []
        for path in non_vocal:
            inputs += ["-i", str(path)]
        filter_complex = f"amix=inputs={len(non_vocal)}:duration=longest"
        proc = await asyncio.create_subprocess_exec(
            ffmpeg, "-y", *inputs, "-filter_complex", filter_complex, str(output_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return None
        return output_path
