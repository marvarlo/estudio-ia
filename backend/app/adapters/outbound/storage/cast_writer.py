"""Escribe personajes.json / escenarios.json / voces.json en el formato que
ya leen los scripts del skill historias-fantasia (assets/personajes_schema.json,
escenarios_schema.json, voces_schema.json) -- para que un proyecto creado
desde la web siga siendo compatible con esas herramientas si hace falta."""
from __future__ import annotations

import json
from pathlib import Path

from app.domain.story.entities import Character, Location, Voice


def write_personajes_json(root: Path, slug: str, characters: list[Character]) -> None:
    payload = {
        "historia": slug,
        "personajes": [
            {
                "id": character.slug,
                "nombre": character.nombre,
                "rol": character.rol,
                "primera_aparicion": "capitulo-1",
                "estado_continuidad": "activo",
                "tokens_visuales_fijos": character.tokens_visuales,
                "outfit_variantes": [],
                "referencia_imagen": {
                    "proveedor": "",
                    "seed_o_id": "",
                    "ruta_imagen_referencia": (
                        str(character.reference_image_path.relative_to(root))
                        if character.reference_image_path
                        else ""
                    ),
                    "paneles": [],
                    "notas_consistencia": "",
                },
                "ficha_sistema": {"clase_o_rol_de_poder": "", "nivel_inicial": "", "nivel_actual": "", "habilidades_clave": []},
                "voz": {"voz_id": "", "proveedor": "ElevenLabs", "notas_direccion": ""},
            }
            for character in characters
        ],
    }
    (root / "personajes.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_escenarios_json(root: Path, slug: str, locations: list[Location]) -> None:
    payload = {
        "historia": slug,
        "escenarios": [
            {
                "id": location.slug,
                "nombre": location.nombre,
                "primera_aparicion": "capitulo-1",
                "descripcion_fija": location.descripcion_fija,
                "descripcion_variantes": [],
                "referencia_imagen": {
                    "ruta_imagen_referencia": (
                        str(location.reference_image_path.relative_to(root)) if location.reference_image_path else ""
                    ),
                    "angulos_adicionales": [],
                    "notas_consistencia": "",
                    "proveedor": "",
                },
            }
            for location in locations
        ],
    }
    (root / "escenarios.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_voces_json(root: Path, slug: str, voices: list[Voice]) -> None:
    """`Voice.personaje_id` ya guarda el slug legible (`protagonista_01`),
    no un id interno de base de datos -- asi lo dejo el importador de la
    fase 0, y AssignVoicesUseCase lo respeta."""
    narrador = next((v for v in voices if v.personaje_id is None), None)
    reparto = [v for v in voices if v.personaje_id is not None]
    payload = {
        "historia": slug,
        "narrador": {"voz_id_referencia": narrador.voice_id_externo if narrador else ""},
        "reparto": [
            {
                "personaje_id": v.personaje_id,
                "voz_id_asignada": v.voice_id_externo,
                "notas_direccion_especificas": v.notas_direccion,
            }
            for v in reparto
        ],
    }
    (root / "voces.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
