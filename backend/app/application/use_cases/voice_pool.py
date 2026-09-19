"""Pool de voces a nivel canal (Paso 8 de SKILL.md) y casting automatico
para un proyecto. La busqueda en vivo contra el catalogo de ElevenLabs
(references/voice_library_search.md del skill original) queda fuera de la
fase 1 -- por ahora el pool se carga a mano (`AddVoiceToPoolUseCase`) y el
casting elige por `veces_usada` mas bajo, igual que documenta el Paso 8."""
from __future__ import annotations

import uuid

from app.adapters.outbound.storage.cast_writer import write_voces_json
from app.application.ports.repository import ProjectRepositoryPort
from app.domain.story.entities import Voice, VoicePoolVoice

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")


class AddVoiceToPoolUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self, proveedor: str, voice_id_externo: str, nombre_interno: str = "", modelo_tts: str = "", atributos: dict | None = None
    ) -> VoicePoolVoice:
        voice = VoicePoolVoice(
            id=str(uuid.uuid5(_NAMESPACE, f"voice-pool/{proveedor}/{voice_id_externo}")),
            proveedor=proveedor,
            voice_id_externo=voice_id_externo,
            nombre_interno=nombre_interno,
            modelo_tts=modelo_tts,
            atributos=atributos or {},
        )
        self._repository.save_pool_voice(voice)
        return voice


class ListVoicePoolUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self) -> list[VoicePoolVoice]:
        return self._repository.list_pool_voices()


class AssignVoicesUseCase:
    """Asigna al narrador (una sola vez a nivel canal, no por proyecto -- si
    ya tiene voz, no se toca) y a cada personaje del proyecto una voz del
    pool, priorizando `veces_usada` mas bajo. Nunca reasigna al narrador de
    un proyecto que ya tiene una fila 'narrador' en Voice."""

    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, project_id: str) -> list[Voice]:
        project = self._repository.get_project(project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {project_id}")
        pool = self._repository.list_pool_voices()
        if not pool:
            raise ValueError("El pool de voces esta vacio -- agrega al menos una voz antes de castear")

        existing = {v.personaje_id: v for v in self._repository.list_voices(project_id)}
        characters = self._repository.list_characters(project_id)

        def pick_least_used(exclude_ids: set[str]) -> VoicePoolVoice:
            candidates = [v for v in pool if v.id not in exclude_ids] or pool
            return min(candidates, key=lambda v: (v.veces_usada, v.ultima_historia or ""))

        used_pool_ids: set[str] = set()
        result: list[Voice] = []

        if None not in existing:
            chosen = pick_least_used(used_pool_ids)
            used_pool_ids.add(chosen.id)
            self._bump_usage(chosen, project.slug)
            voice = Voice(
                id=str(uuid.uuid5(_NAMESPACE, f"voice/{project_id}/narrador")),
                project_id=project_id,
                personaje_id=None,
                proveedor=chosen.proveedor,
                voice_id_externo=chosen.voice_id_externo,
                modelo_tts=chosen.modelo_tts,
                notas_direccion="Narrador",
            )
            self._repository.save_voice(voice)
            result.append(voice)
        else:
            result.append(existing[None])

        for character in characters:
            if character.slug in existing:
                result.append(existing[character.slug])
                continue
            chosen = pick_least_used(used_pool_ids)
            used_pool_ids.add(chosen.id)
            self._bump_usage(chosen, project.slug)
            voice = Voice(
                id=str(uuid.uuid5(_NAMESPACE, f"voice/{project_id}/{character.slug}")),
                project_id=project_id,
                personaje_id=character.slug,
                proveedor=chosen.proveedor,
                voice_id_externo=chosen.voice_id_externo,
                modelo_tts=chosen.modelo_tts,
                notas_direccion=f"Voz de {character.nombre}",
            )
            self._repository.save_voice(voice)
            result.append(voice)

        write_voces_json(project.root_path, project.slug, result)
        return result

    def _bump_usage(self, pool_voice: VoicePoolVoice, slug: str) -> None:
        pool_voice.veces_usada += 1
        pool_voice.ultima_historia = slug
        self._repository.save_pool_voice(pool_voice)
