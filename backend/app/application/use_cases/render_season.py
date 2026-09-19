"""Corte de TEMPORADA COMPLETA: concatena los capitulos ya renderizados
individualmente (fase 3) con separadores "Capitulo N: Titulo" entre cada
uno y un cartel de cierre al final -- misma idea que build_season.py del
skill original (Separador/Cierre + concat de ffmpeg, sin recodificar,
porque todos los clips salen del mismo proyecto Remotion con el mismo
codec/resolucion/fps), pero disparado desde la web en vez de a mano.

No renderiza los capitulos individuales -- esos tienen que existir de
antemano (RenderChapterUseCase, fase 3)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.application.ports.media_probe import MediaProbePort
from app.application.ports.render import RenderPort, RenderRequest
from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset


class RenderSeasonUseCase:
    def __init__(self, repository: ProjectRepositoryPort, render_port: RenderPort, media_probe: MediaProbePort) -> None:
        self._repository = repository
        self._render_port = render_port
        self._media_probe = media_probe

    async def execute(self, project_id: str) -> Asset:
        project = self._repository.get_project(project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {project_id}")
        chapters = sorted(self._repository.list_chapters(project_id), key=lambda c: c.numero)
        if not chapters:
            raise ValueError("Este proyecto todavia no tiene capitulos")

        assets_by_id = {a.id: a for a in self._repository.list_assets(project_id)}
        clips: list[Path] = []
        season_dir = project.root_path / "temporada"
        season_dir.mkdir(parents=True, exist_ok=True)

        for i, chapter in enumerate(chapters):
            if chapter.selected_render_asset_id is None:
                raise ValueError(
                    f"El capitulo {chapter.numero} ({chapter.titulo}) todavia no fue renderizado -- "
                    "renderiza todos los capitulos antes del corte de temporada"
                )
            chapter_asset = assets_by_id.get(chapter.selected_render_asset_id)
            if chapter_asset is None or not chapter_asset.path.exists():
                raise ValueError(f"El render seleccionado del capitulo {chapter.numero} ya no existe en disco")

            if i > 0:
                separador_path = season_dir / f"separador-{chapter.numero}.mp4"
                separador_result = await self._render_port.render(
                    RenderRequest(
                        composition_id="Separador",
                        timeline={"numeroCapitulo": chapter.numero, "tituloCapitulo": chapter.titulo},
                        output_path=separador_path,
                        public_dir=project.root_path,
                    )
                )
                clips.append(separador_result.output_path)

            clips.append(chapter_asset.path)

        cierre_path = season_dir / "cierre.mp4"
        cierre_result = await self._render_port.render(
            RenderRequest(composition_id="Cierre", timeline={}, output_path=cierre_path, public_dir=project.root_path)
        )
        clips.append(cierre_result.output_path)

        final_output = season_dir / f"temporada-{uuid.uuid4().hex[:8]}.mp4"
        concat_result = await self._render_port.concat(clips, final_output)

        asset = Asset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            chapter_id=None,
            shot_id=None,
            kind=AssetKind.VIDEO,
            path=concat_result.output_path,
            provider="remotion",
            model="Temporada",
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        project.selected_season_asset_id = asset.id
        self._repository.save_project(project)

        return asset
