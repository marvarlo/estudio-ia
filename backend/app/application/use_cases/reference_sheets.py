"""Casos de uso de generacion de fichas de referencia (Paso 7/8 de
SKILL.md, comando `crear-fichas-personajes`) -- la imagen ancla que despues
mantiene consistente al personaje/escenario en todas las escenas."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.outbound.image.image_dimensions import png_dimensions
from app.application.ports.image_generation import ImageGenerationPort, ImageGenerationRequest
from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset
from app.prompts.reference_sheets import build_character_sheet_prompt, build_location_sheet_prompt

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")
# Panorama ancho: deja espacio para una fila de 4 cuerpos completos + 4 rostros,
# igual que SHEET_ASPECT_RATIO en create_character_sheets.py.
SHEET_WIDTH, SHEET_HEIGHT = 1920, 1080


class GenerateCharacterSheetUseCase:
    def __init__(self, repository: ProjectRepositoryPort, image_port: ImageGenerationPort) -> None:
        self._repository = repository
        self._image_port = image_port

    async def execute(self, character_id: str) -> Asset:
        character = self._repository.get_character(character_id)
        if character is None:
            raise ValueError(f"Personaje no encontrado: {character_id}")
        project = self._repository.get_project(character.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {character.project_id}")

        prompt = build_character_sheet_prompt(project.estilo_visual, character)
        result = await self._image_port.generate(
            ImageGenerationRequest(prompt=prompt, width=SHEET_WIDTH, height=SHEET_HEIGHT)
        )

        output_path = project.root_path / "referencias" / "personajes" / f"{character.slug}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result.image_bytes)

        try:
            width, height = png_dimensions(result.image_bytes)
        except ValueError:
            width, height = result.width, result.height

        asset = Asset(
            id=str(uuid.uuid5(_NAMESPACE, f"sheet/character/{character_id}")),
            project_id=character.project_id,
            kind=AssetKind.SHEET,
            path=output_path,
            width=width,
            height=height,
            provider=result.provider,
            model=result.model,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        character.reference_image_path = output_path
        self._repository.save_character(character)
        return asset


class GenerateLocationSheetUseCase:
    def __init__(self, repository: ProjectRepositoryPort, image_port: ImageGenerationPort) -> None:
        self._repository = repository
        self._image_port = image_port

    async def execute(self, location_id: str) -> Asset:
        location = self._repository.get_location(location_id)
        if location is None:
            raise ValueError(f"Escenario no encontrado: {location_id}")
        project = self._repository.get_project(location.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {location.project_id}")

        prompt = build_location_sheet_prompt(project.estilo_visual, location)
        result = await self._image_port.generate(
            ImageGenerationRequest(prompt=prompt, width=SHEET_WIDTH, height=SHEET_HEIGHT)
        )

        output_path = project.root_path / "referencias" / "escenarios" / f"{location.slug}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(result.image_bytes)

        try:
            width, height = png_dimensions(result.image_bytes)
        except ValueError:
            width, height = result.width, result.height

        asset = Asset(
            id=str(uuid.uuid5(_NAMESPACE, f"sheet/location/{location_id}")),
            project_id=location.project_id,
            kind=AssetKind.SHEET,
            path=output_path,
            width=width,
            height=height,
            provider=result.provider,
            model=result.model,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_asset(asset)

        location.reference_image_path = output_path
        self._repository.save_location(location)
        return asset
