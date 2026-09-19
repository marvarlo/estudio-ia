import pytest

from app.application.use_cases.story_generation import CreateStoryProjectUseCase
from app.application.use_cases.voice_pool import AddVoiceToPoolUseCase, AssignVoicesUseCase, ListVoicePoolUseCase
from app.domain.story.entities import Character


def _add_voice(repository, external_id: str):
    return AddVoiceToPoolUseCase(repository).execute(
        proveedor="ElevenLabs", voice_id_externo=external_id, nombre_interno=external_id
    )


def test_add_and_list_pool_voices(repository):
    _add_voice(repository, "voice-a")
    _add_voice(repository, "voice-b")

    voices = ListVoicePoolUseCase(repository).execute()

    assert {v.voice_id_externo for v in voices} == {"voice-a", "voice-b"}
    assert all(v.veces_usada == 0 for v in voices)


def test_assign_voices_raises_when_pool_empty(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Sin Pool")
    with pytest.raises(ValueError, match="pool"):
        AssignVoicesUseCase(repository).execute(project.id)


def test_assign_voices_picks_least_used_and_bumps_usage(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Con Pool")
    repository.save_character(Character(id="c1", project_id=project.id, slug="protagonista_01", nombre="Vera"))
    voice_a = _add_voice(repository, "voice-a")
    voice_b = _add_voice(repository, "voice-b")

    voices = AssignVoicesUseCase(repository).execute(project.id)

    assert len(voices) == 2  # narrador + 1 personaje
    narrador = next(v for v in voices if v.personaje_id is None)
    personaje = next(v for v in voices if v.personaje_id == "protagonista_01")
    assert {narrador.voice_id_externo, personaje.voice_id_externo} == {"voice-a", "voice-b"}

    pool_after = {v.id: v for v in ListVoicePoolUseCase(repository).execute()}
    assert pool_after[voice_a.id].veces_usada == 1
    assert pool_after[voice_b.id].veces_usada == 1
    assert pool_after[voice_a.id].ultima_historia == project.slug

    voces_json = (project.root_path / "voces.json").read_text(encoding="utf-8")
    assert "protagonista_01" in voces_json


def test_assign_voices_does_not_reassign_existing_narrator(tmp_path, repository):
    project = CreateStoryProjectUseCase(repository, tmp_path).execute(name="Reasignacion")
    _add_voice(repository, "voice-a")

    first_pass = AssignVoicesUseCase(repository).execute(project.id)
    second_pass = AssignVoicesUseCase(repository).execute(project.id)

    narrador_1 = next(v for v in first_pass if v.personaje_id is None)
    narrador_2 = next(v for v in second_pass if v.personaje_id is None)
    assert narrador_1.id == narrador_2.id

    pool_voice = ListVoicePoolUseCase(repository).execute()[0]
    assert pool_voice.veces_usada == 1  # no se incrementa de nuevo en el segundo pase
