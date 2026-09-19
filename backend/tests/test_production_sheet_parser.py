from app.adapters.outbound.storage.production_sheet_parser import parse_production_sheet

SAMPLE = """
# Capítulo 1 — Ejemplo

| # | Tipo | Personaje | Escenario | Momento Dia | Texto | Prompt Imagen | Prompt Video | Movimiento Camara | Duracion | SFX/Musica |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Narracion |  |  | noche | Primera linea. | un espejo agrietado |  | zoom in lento | 2.8s | musica de tension |
| 2 | Narracion | protagonista_01 | pueblo_miralda | amanecer | Segunda linea. | [protagonista_01] caminando |  | pan izquierda | 4.8s |  |
| 3 | Dialogo | protagonista_01 |  |  | Tercera linea. | primer plano | Action: habla | zoom in lento | 1.6s |  |
"""


def test_parses_rows_and_ignores_header_and_separator():
    rows = parse_production_sheet(SAMPLE)
    assert len(rows) == 3
    assert rows[0].orden == 1
    assert rows[0].tipo == "Narracion"
    assert rows[0].momento_dia == "noche"
    assert rows[0].duracion_estimada_seg == 2.8


def test_carries_forward_escenario_and_momento_dia():
    rows = parse_production_sheet(SAMPLE)
    # La fila 3 no repite Escenario/Momento Dia -- deben heredarse de la fila 2,
    # igual que documenta references/formato_produccion.md del skill original.
    assert rows[2].escenario_id == "pueblo_miralda"
    assert rows[2].momento_dia == "amanecer"


def test_splits_multiple_personajes():
    text = SAMPLE.replace(
        "| 3 | Dialogo | protagonista_01 |",
        "| 3 | Dialogo | protagonista_01, secundario_01 |",
    )
    rows = parse_production_sheet(text)
    assert rows[2].personaje_ids == ["protagonista_01", "secundario_01"]


def test_empty_sheet_returns_no_rows():
    assert parse_production_sheet("# Solo un titulo, sin tabla\n") == []
