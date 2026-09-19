import json

import pytest

from app.adapters.outbound.analysis.librosa_music_analysis import LibrosaMusicAnalysisAdapter
from app.application.ports.media_probe import MediaInfo
from app.application.ports.music_analysis import MusicAnalysisResult
from app.application.ports.text_generation import TextGenerationRequest, TextGenerationResult
from app.application.use_cases.music_track import (
    CreateTrackProjectUseCase,
    GenerateMusicCastUseCase,
    GenerateMusicVideoShotsUseCase,
    TranscribeTrackUseCase,
    _build_beat_aligned_windows,
)
from app.application.ports.transcription import TranscribedWord, TranscriptionResult
from app.domain.shared.value_objects import ShotType
from app.prompts.music_cast import MusicCastBrief

MUSIC_CAST_JSON = {
    "personajes": [
        {
            "id": "protagonista_01", "nombre": "Nova", "rol": "protagonista",
            "descripcion_corta": "a lonely dancer", "cabello": "short silver hair", "ojos": "violet eyes",
            "marca_distintiva": "glowing tattoo", "atuendo_base": "iridescent jacket",
            "prompt_anchor": "Nova, lonely dancer, short silver hair, violet eyes, glowing tattoo, iridescent jacket",
        }
    ],
    "escenarios": [{"id": "neon_rooftop", "nombre": "Neon Rooftop", "descripcion_fija": "a rain-soaked neon rooftop at night"}],
}


class FakeMediaProbe:
    def __init__(self, duration: float = 30.0) -> None:
        self.duration = duration

    def probe(self, path):
        return MediaInfo(duration_seconds=self.duration)


class FakeTextPort:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.last_request: TextGenerationRequest | None = None

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        self.last_request = request
        return TextGenerationResult(text=self._response_text, model="fake-model", provider="fake")

    async def health_check(self):  # pragma: no cover
        raise NotImplementedError


class FakeTranscriptionPort:
    def __init__(self, words: list[TranscribedWord]) -> None:
        self._words = words

    async def transcribe(self, audio_path, language=None) -> TranscriptionResult:
        return TranscriptionResult(words=self._words, language="es", raw_text=" ".join(w.text for w in self._words))

    async def health_check(self):  # pragma: no cover
        raise NotImplementedError


class FakeMusicAnalysisPort:
    def __init__(self, beats: list[float] | None = None) -> None:
        self._beats = beats or []

    async def analyze(self, audio_path) -> MusicAnalysisResult:
        return MusicAnalysisResult(bpm=120.0 if self._beats else None, key=None, sections=[], beats=self._beats)


async def _setup_track_with_lyrics(tmp_path, repository, duration=30.0):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe(duration)).execute(
        name="Music Video Test", kind="music_video", audio_bytes=b"fake-mp3", audio_filename="song.mp3"
    )
    words = [
        TranscribedWord(text="Nova", start=1.0, end=1.4, probability=0.9),
        TranscribedWord(text="baila", start=1.4, end=1.9, probability=0.9),
        TranscribedWord(text="sola", start=1.9, end=2.3, probability=0.9),
        TranscribedWord(text="bajo", start=15.0, end=15.3, probability=0.9),
        TranscribedWord(text="neon", start=15.3, end=15.8, probability=0.9),
    ]
    await TranscribeTrackUseCase(repository, FakeTranscriptionPort(words)).execute(result.track.id)
    return result


async def test_generate_music_cast_creates_characters_and_locations(tmp_path, repository):
    result = await _setup_track_with_lyrics(tmp_path, repository)
    fake_port = FakeTextPort(json.dumps(MUSIC_CAST_JSON))

    cast = await GenerateMusicCastUseCase(repository, fake_port).execute(
        result.track.id, MusicCastBrief(estilo_visual="anime")
    )

    assert len(cast.characters) == 1
    assert cast.characters[0].slug == "protagonista_01"
    assert len(cast.locations) == 1
    assert cast.locations[0].slug == "neon_rooftop"
    assert "Nova baila sola" in fake_port.last_request.prompt

    reloaded = repository.list_characters(result.project.id)
    assert len(reloaded) == 1


async def test_generate_music_cast_raises_without_lyrics(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
        name="No Lyrics", kind="music_video", audio_bytes=b"x", audio_filename="x.mp3"
    )
    with pytest.raises(ValueError, match="letra"):
        await GenerateMusicCastUseCase(repository, FakeTextPort("{}")).execute(result.track.id, MusicCastBrief())


def test_build_beat_aligned_windows_snaps_to_nearest_beat():
    beats = [0.5, 4.0, 7.9, 8.5, 12.0, 16.1, 20.0, 24.05, 28.0]
    windows = _build_beat_aligned_windows(total_duration=30.0, window_seconds=8.0, beats=beats)

    assert windows[0][0] == 0.0
    # La primer ventana termina cerca de 8s -- debe snappear a 7.9, no seguir en 8.0 a ciegas.
    assert windows[0][1] == pytest.approx(7.9)
    assert windows[1][0] == pytest.approx(7.9)
    # Cubre toda la duracion sin huecos ni superposiciones.
    for (s1, e1), (s2, _e2) in zip(windows, windows[1:]):
        assert e1 == s2
    assert windows[-1][1] == 30.0


def test_build_beat_aligned_windows_falls_back_to_fixed_without_beats():
    windows = _build_beat_aligned_windows(total_duration=20.0, window_seconds=8.0, beats=[])
    assert windows == [(0.0, 8.0), (8.0, 16.0), (16.0, 20.0)]


async def test_generate_music_video_shots_creates_windows_with_cast_and_content(tmp_path, repository):
    result = await _setup_track_with_lyrics(tmp_path, repository, duration=20.0)
    await GenerateMusicCastUseCase(repository, FakeTextPort(json.dumps(MUSIC_CAST_JSON))).execute(
        result.track.id, MusicCastBrief()
    )
    music_analysis = FakeMusicAnalysisPort(beats=[7.5, 15.0])

    shots = await GenerateMusicVideoShotsUseCase(repository, music_analysis).execute(
        result.chapter.id, result.track.id, window_seconds=8.0
    )

    assert len(shots) >= 2
    assert shots[0].personaje_ids == ["protagonista_01"]
    assert shots[0].escenario_id == "neon_rooftop"
    assert shots[0].tipo == ShotType.LETRA  # tiene letra superpuesta (Nova baila sola, 1.0-2.3s)
    assert "no readable text" in shots[0].prompt_imagen.lower()
    assert "nova baila sola" in shots[0].prompt_imagen.lower()


async def test_generate_music_video_shots_marks_instrumental_windows(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe(16.0)).execute(
        name="Instrumental Test", kind="music_video", audio_bytes=b"x", audio_filename="x.mp3"
    )
    shots = await GenerateMusicVideoShotsUseCase(repository, FakeMusicAnalysisPort()).execute(
        result.chapter.id, result.track.id, window_seconds=8.0
    )
    assert all(s.tipo == ShotType.INSTRUMENTAL for s in shots)
    assert all(s.personaje_ids == [] for s in shots)


async def test_librosa_adapter_returns_empty_result_on_invalid_file(tmp_path):
    adapter = LibrosaMusicAnalysisAdapter()
    missing = tmp_path / "does-not-exist.mp3"

    result = await adapter.analyze(missing)

    assert result.bpm is None
    assert result.beats == []
