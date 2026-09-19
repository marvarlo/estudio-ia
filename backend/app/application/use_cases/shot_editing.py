"""CRUD y reordenado de shots -- esto es lo que hace la tabla de produccion
"editable en la web" (decision confirmada por el usuario en la seccion 11
del doc de arquitectura: la web es la fuente de verdad, produccion.md queda
como entrada inicial de importacion / salida de exportacion)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.application.ports.repository import ProjectRepositoryPort
from app.domain.shared.value_objects import ShotType
from app.domain.story.entities import Shot

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")


@dataclass
class ShotInput:
    tipo: str = "Narracion"
    personaje_ids: list[str] = field(default_factory=list)
    escenario_id: str | None = None
    sub_escenario: str = ""
    momento_dia: str = ""
    texto: str = ""
    prompt_imagen: str = ""
    prompt_video: str = ""
    movimiento_camara: str = ""
    duracion_estimada_seg: float | None = None
    sfx_musica: str = ""


def _apply(shot: Shot, data: ShotInput) -> None:
    shot.tipo = ShotType(data.tipo) if data.tipo in ("Narracion", "Dialogo") else ShotType.NARRACION
    shot.personaje_ids = data.personaje_ids
    shot.escenario_id = data.escenario_id
    shot.sub_escenario = data.sub_escenario
    shot.momento_dia = data.momento_dia
    shot.texto = data.texto
    shot.prompt_imagen = data.prompt_imagen
    shot.prompt_video = data.prompt_video
    shot.movimiento_camara = data.movimiento_camara
    shot.duracion_estimada_seg = data.duracion_estimada_seg
    shot.sfx_musica = data.sfx_musica


class CreateShotUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, chapter_id: str, data: ShotInput) -> Shot:
        existing = self._repository.list_shots(chapter_id)
        next_orden = (max((s.orden for s in existing), default=0)) + 1
        shot = Shot(id=str(uuid.uuid4()), chapter_id=chapter_id, orden=next_orden, tipo=ShotType.NARRACION)
        _apply(shot, data)
        self._repository.save_shot(shot)
        return shot


class UpdateShotUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, shot_id: str, data: ShotInput) -> Shot:
        shot = self._repository.get_shot(shot_id)
        if shot is None:
            raise ValueError(f"Shot no encontrado: {shot_id}")
        _apply(shot, data)
        self._repository.save_shot(shot)
        return shot


class DeleteShotUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, shot_id: str) -> None:
        self._repository.delete_shot(shot_id)


class ReorderShotsUseCase:
    """Recibe la lista completa de shot ids en el orden deseado y reasigna
    `orden` de forma secuencial (1..N) -- mas simple y menos propenso a
    errores que aceptar una posicion puntual de insercion."""

    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, chapter_id: str, ordered_shot_ids: list[str]) -> list[Shot]:
        shots_by_id = {s.id: s for s in self._repository.list_shots(chapter_id)}
        missing = [sid for sid in ordered_shot_ids if sid not in shots_by_id]
        if missing:
            raise ValueError(f"Ids de shot desconocidos para este capitulo: {missing}")
        if len(ordered_shot_ids) != len(shots_by_id):
            raise ValueError("La lista de reordenado debe incluir todos los shots del capitulo")

        result = []
        for index, shot_id in enumerate(ordered_shot_ids, start=1):
            shot = shots_by_id[shot_id]
            shot.orden = index
            self._repository.save_shot(shot)
            result.append(shot)
        return result
