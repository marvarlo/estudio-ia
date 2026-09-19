"""Genera UNA imagen para un shot puntual (comando `crear-imagenes` /
`crear-imagenes-local` del skill original, pero fila por fila y encolado
como Job -- ver seccion 8 del doc de arquitectura). Cada llamada crea un
Asset NUEVO (nunca sobreescribe) y lo selecciona automaticamente salvo que
se pida lo contrario -- 'Regla de versionado' de la seccion 3."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.outbound.image.image_dimensions import png_dimensions
from app.application.ports.image_generation import ImageGenerationPort, ImageGenerationRequest
from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset
from app.prompts.shot_image import build_deterministic_prompt, build_reference_request

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1280, 720


class GenerateShotImageUseCase:
    def __init__(self, repository: ProjectRepositoryPort, image_port: ImageGenerationPort, supports_references: bool) -> None:
        """`supports_references`: True para proveedores que aceptan imagenes
        de referencia (Gemini) -- la identidad se ancla por imagen y el
        texto solo describe la accion. False para proveedores locales sin
        esa capacidad (Lemonade) -- toda la identidad visual se carga como
        texto en cada llamada (ver references/generacion_local_lemonade.md
        del skill original)."""
        self._repository = repository
        self._image_port = image_port
        self._supports_references = supports_references

    async def execute(self, shot_id: str, *, select: bool = True, width: int | None = None, height: int | None = None) -> Asset:
        shot = self._repository.get_shot(shot_id)
        if shot is None:
            raise ValueError(f"Shot no encontrado: {shot_id}")
        chapter = self._repository.get_chapter(shot.chapter_id)
        if chapter is None:
            raise ValueError(f"Capitulo no encontrado: {shot.chapter_id}")
        project = self._repository.get_project(chapter.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {chapter.project_id}")

        characters_by_slug = {c.slug: c for c in self._repository.list_characters(project.id)}
        locations_by_slug = {l.slug: l for l in self._repository.list_locations(project.id)}

        reference_paths: list[Path] = []
        reference_labels: list[str] = []
        if self._supports_references:
            prompt, reference_paths, reference_labels = build_reference_request(shot, characters_by_slug, locations_by_slug)
        else:
            prompt = build_deterministic_prompt(shot, characters_by_slug, locations_by_slug, project.estilo_visual)

        request = ImageGenerationRequest(
            prompt=prompt,
            width=width or DEFAULT_WIDTH,
            height=height or DEFAULT_HEIGHT,
            reference_images=reference_paths,
            reference_labels=reference_labels,
        )
        result = await self._image_port.generate(request)

        try:
            real_width, real_height = png_dimensions(result.image_bytes)
        except ValueError:
            real_width, real_height = result.width, result.height

        chapter_dir = project.root_path / f"capitulo-{chapter.numero}"
        formato_dir = chapter_dir / "assets" / f"{real_width}x{real_height}" / "imagenes"
        formato_dir.mkdir(parents=True, exist_ok=True)
        output_path = formato_dir / f"capitulo{chapter.numero}-escena{shot.orden:02d}-{uuid.uuid4().hex[:8]}.png"
        output_path.write_bytes(result.image_bytes)

        asset = Asset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            chapter_id=chapter.id,
            shot_id=shot.id,
            kind=AssetKind.IMAGE,
            path=output_path,
            width=real_width,
            height=real_height,
            provider=result.provider,
            model=result.model,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        if select:
            shot.selected_image_asset_id = asset.id
            self._repository.save_shot(shot)

        formatos = set(project.formatos)
        formatos.add(f"{real_width}x{real_height}")
        if formatos != set(project.formatos):
            project.formatos = sorted(formatos)
            self._repository.save_project(project)

        return asset
