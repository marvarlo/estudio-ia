"""Regresion: ShotOut debe mostrar el asset SELECCIONADO de cada tipo, no
'cualquiera que exista' -- bug real encontrado en verificacion manual: un
shot con dos imagenes (una importada, una recien generada) seguia mostrando
la importada porque el resolver tomaba la primera imagen de la lista en vez
de mirar `shot.selected_image_asset_id`."""
from pathlib import Path

from app.adapters.inbound.api.schemas import ChapterShotsOut
from app.domain.shared.value_objects import AssetKind, ChapterStatus, ShotType
from app.domain.story.entities import Asset, Chapter, Shot


def test_shot_out_resolves_the_selected_asset_not_the_first_one():
    shot = Shot(id="shot-1", chapter_id="chapter-1", orden=1, tipo=ShotType.NARRACION, texto="x")
    older = Asset(id="older", project_id="p1", chapter_id="chapter-1", shot_id="shot-1", kind=AssetKind.IMAGE, path=Path("older.png"))
    newer = Asset(id="newer", project_id="p1", chapter_id="chapter-1", shot_id="shot-1", kind=AssetKind.IMAGE, path=Path("newer.png"))
    shot.selected_image_asset_id = newer.id

    chapter = Chapter(id="chapter-1", project_id="p1", numero=1, titulo="Uno", estado=ChapterStatus.ASSETS)
    out = ChapterShotsOut.from_domain(chapter, [shot], [older, newer])

    assert out.shots[0].image_asset_path == "newer.png"


def test_shot_out_shows_no_image_when_nothing_selected():
    shot = Shot(id="shot-1", chapter_id="chapter-1", orden=1, tipo=ShotType.NARRACION, texto="x")
    orphan = Asset(id="orphan", project_id="p1", chapter_id="chapter-1", shot_id="shot-1", kind=AssetKind.IMAGE, path=Path("x.png"))

    chapter = Chapter(id="chapter-1", project_id="p1", numero=1, titulo="Uno", estado=ChapterStatus.HOJA_DERIVADA)
    out = ChapterShotsOut.from_domain(chapter, [shot], [orphan])

    assert out.shots[0].image_asset_path is None
