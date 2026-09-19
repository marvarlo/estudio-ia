"""Historial de versiones por shot (seccion 3 del doc de arquitectura,
'Regla de versionado'): cada generacion crea un Asset nuevo sin borrar los
anteriores; estos casos de uso listan ese historial y permiten volver a
elegir una version previa sin regenerar nada."""
from __future__ import annotations

from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import AssetKind
from app.domain.story.entities import Asset, Shot

_SELECTED_FIELD_BY_KIND = {
    AssetKind.IMAGE: "selected_image_asset_id",
    AssetKind.AUDIO: "selected_audio_asset_id",
    AssetKind.VIDEO: "selected_video_asset_id",
}


class ListShotAssetsUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, shot_id: str) -> list[Asset]:
        return self._repository.list_assets_for_shot(shot_id)


class SelectShotAssetUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, shot_id: str, asset_id: str) -> Shot:
        shot = self._repository.get_shot(shot_id)
        if shot is None:
            raise ValueError(f"Shot no encontrado: {shot_id}")
        asset = self._repository.get_asset(asset_id)
        if asset is None:
            raise ValueError(f"Asset no encontrado: {asset_id}")
        if asset.shot_id != shot_id:
            raise ValueError("Ese asset no pertenece a este shot")
        field = _SELECTED_FIELD_BY_KIND.get(asset.kind)
        if field is None:
            raise ValueError(f"No se puede seleccionar un asset de tipo {asset.kind.value} para un shot")
        setattr(shot, field, asset.id)
        self._repository.save_shot(shot)
        return shot
