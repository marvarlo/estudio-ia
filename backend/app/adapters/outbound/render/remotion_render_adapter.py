"""Implementacion de RenderPort: invoca el sidecar Remotion en `render/`
como subproceso de `node` (via su CLI, `remotion-cli.js render ...`).

No usamos `npx remotion render` a proposito: en esta maquina Windows, invocar
"npx" (via .cmd o via cmd.exe /c) desde subprocess falla por un AutoRun de
cmd.exe roto ("DOSKEY no se reconoce") -- nada que ver con Remotion. El truco
para evitarlo (ya verificado por build_season.py del skill original) es ir
directo al entry point real de la CLI con node.exe, que es justo lo que
node_modules/.bin/remotion.cmd hace por debajo.

`render/remotion.config.ts` lee la variable de entorno RENDER_PUBLIC_DIR
para servir los assets del capitulo (imagen/audio/video referenciados en
`timeline` son rutas relativas a esa carpeta, via staticFile()) -- ver
Capitulo.tsx. Esto evita tener que re-empaquetar Remotion por cada request:
cada render es una invocacion de proceso fresca, asi que la variable de
entorno cambia libremente entre un capitulo y otro sin estado compartido.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from app.application.ports.media_probe import MediaProbePort
from app.application.ports.render import RenderRequest, RenderResult


class RemotionRenderAdapter:
    def __init__(self, render_project_dir: Path, media_probe: MediaProbePort) -> None:
        self._project_dir = render_project_dir
        self._media_probe = media_probe

    def _node_and_cli(self) -> tuple[str, Path]:
        node = shutil.which("node")
        if node is None:
            raise RuntimeError("No se encontro node.exe en el PATH -- necesario para el sidecar de Remotion")
        cli = self._project_dir / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
        if not cli.exists():
            raise RuntimeError(
                f"No se encontro {cli} -- corre 'npm install' en {self._project_dir} primero (ver render/README.md)"
            )
        return node, cli

    async def render(self, request: RenderRequest) -> RenderResult:
        node, cli = self._node_and_cli()
        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=request.output_path.parent, encoding="utf-8"
        ) as props_file:
            json.dump({"timeline": request.timeline}, props_file, ensure_ascii=False)
            props_path = Path(props_file.name)

        try:
            cmd = [
                node,
                str(cli),
                "render",
                request.composition_id,
                str(request.output_path),
                f"--props={props_path}",
            ]
            env = {**os.environ, "RENDER_PUBLIC_DIR": str(request.public_dir)}
            proc = await asyncio.create_subprocess_exec(
                *cmd, cwd=str(self._project_dir), env=env,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Remotion fallo al renderizar '{request.composition_id}' (exit {proc.returncode}):\n"
                    f"{stderr.decode(errors='replace')}\n{stdout.decode(errors='replace')}"
                )
        finally:
            props_path.unlink(missing_ok=True)

        info = self._media_probe.probe(request.output_path)
        return RenderResult(output_path=request.output_path, duration_seconds=info.duration_seconds or 0.0)

    async def concat(self, clips: list[Path], output_path: Path) -> RenderResult:
        """Concatena clips ya renderizados con el mismo codec/resolucion/fps
        (todos salen del mismo proyecto Remotion) via el demuxer `concat` de
        ffmpeg -- sin recodificar. Usado para el corte de temporada completa
        (fase 5), no para un capitulo individual."""
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError("No se encontro ffmpeg en el PATH")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, dir=output_path.parent, encoding="utf-8"
        ) as list_file:
            for clip in clips:
                list_file.write(f"file '{clip.resolve().as_posix()}'\n")
            list_path = Path(list_file.name)

        try:
            proc = await asyncio.create_subprocess_exec(
                ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output_path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg fallo al concatenar: {stderr.decode(errors='replace')}")
        finally:
            list_path.unlink(missing_ok=True)

        info = self._media_probe.probe(output_path)
        return RenderResult(output_path=output_path, duration_seconds=info.duration_seconds or 0.0)
