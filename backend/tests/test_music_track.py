import pytest

from app.application.ports.media_probe import MediaInfo
from app.application.ports.transcription import TranscribedWord, TranscriptionResult
from app.application.use_cases.music_track import (
    CreateTrackProjectUseCase,
    DeleteLyricLineUseCase,
    GenerateShotsFromLyricsUseCase,
    TranscribeTrackUseCase,
    UpdateLyricLineUseCase,
)
from app.domain.shared.value_objects import ProjectKind, ShotType


class FakeMediaProbe:
    def __init__(self, duration: float = 12.0) -> None:
        self.duration = duration

    def probe(self, path):
        return MediaInfo(duration_seconds=self.duration)


class FakeTranscriptionPort:
    def __init__(self, words: list[TranscribedWord]) -> None:
        self._words = words
        self.last_path = None

    async def transcribe(self, audio_path, language=None) -> TranscriptionResult:
        self.last_path = audio_path
        return TranscriptionResult(words=self._words, language="es", raw_text=" ".join(w.text for w in self._words))

    async def health_check(self):  # pragma: no cover
        raise NotImplementedError


def test_create_track_project_creates_project_chapter_and_track(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe(42.0)).execute(
        name="Mi Cancion", kind="lyrics_video", audio_bytes=b"fake-mp3-bytes", audio_filename="song.mp3"
    )

    assert result.project.kind == ProjectKind.LYRICS_VIDEO
    assert result.chapter.numero == 1
    assert result.track.duration_seconds == 42.0
    assert result.track.source_path.endswith("track.mp3")
    from pathlib import Path
    assert Path(result.track.source_path).exists()
    assert Path(result.track.source_path).read_bytes() == b"fake-mp3-bytes"

    reloaded = repository.get_track(result.track.id)
    assert reloaded is not None
    assert reloaded.project_id == result.project.id


def test_create_track_project_rejects_non_music_kind(tmp_path, repository):
    with pytest.raises(ValueError, match="kind"):
        CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
            name="X", kind="story", audio_bytes=b"x", audio_filename="x.mp3"
        )


async def test_transcribe_track_splits_into_lines_on_silence_gap(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
        name="Gap Test", kind="karaoke", audio_bytes=b"x", audio_filename="x.mp3"
    )
    words = [
        TranscribedWord(text="Hola", start=0.0, end=0.3, probability=0.99),
        TranscribedWord(text="mundo", start=0.3, end=0.6, probability=0.98),
        # salto > 1.2s: nueva linea
        TranscribedWord(text="Adios", start=3.0, end=3.4, probability=0.95),
    ]
    port = FakeTranscriptionPort(words)

    lines = await TranscribeTrackUseCase(repository, port).execute(result.track.id)

    assert len(lines) == 2
    assert lines[0].text == "Hola mundo"
    assert lines[0].start == 0.0 and lines[0].end == 0.6
    assert lines[1].text == "Adios"
    assert port.last_path.name == "track.mp3"

    reloaded = repository.list_lyric_lines(result.track.id)
    assert len(reloaded) == 2
    assert reloaded[1].words[0].text == "Adios"


async def test_transcribe_track_flags_suspect_words(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
        name="Suspect Test", kind="lyrics_video", audio_bytes=b"x", audio_filename="x.mp3"
    )
    words = [TranscribedWord(text="ruido", start=0.0, end=6.0, probability=0.1, suspect=True)]
    port = FakeTranscriptionPort(words)

    lines = await TranscribeTrackUseCase(repository, port).execute(result.track.id)

    assert lines[0].words[0].suspect is True


def test_update_and_delete_lyric_line(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
        name="Edit Test", kind="lyrics_video", audio_bytes=b"x", audio_filename="x.mp3"
    )
    from app.domain.music.entities import LyricLine
    line = LyricLine(id="line-1", track_id=result.track.id, index=0, text="orig", start=0.0, end=1.0)
    repository.replace_lyric_lines(result.track.id, [line])

    updated = UpdateLyricLineUseCase(repository).execute("line-1", text="corregido", start=0.1, end=1.2)
    assert updated.text == "corregido"
    assert updated.start == 0.1

    DeleteLyricLineUseCase(repository).execute("line-1")
    assert repository.get_lyric_line("line-1") is None


def test_generate_shots_from_lyrics_creates_one_shot_per_line(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
        name="Shots Test", kind="lyrics_video", audio_bytes=b"x", audio_filename="x.mp3"
    )
    from app.domain.music.entities import LyricLine
    lines = [
        LyricLine(id="l1", track_id=result.track.id, index=0, text="primera linea", start=0.0, end=2.0),
        LyricLine(id="l2", track_id=result.track.id, index=1, text="segunda linea", start=2.0, end=5.0),
    ]
    repository.replace_lyric_lines(result.track.id, lines)

    shots = GenerateShotsFromLyricsUseCase(repository).execute(result.chapter.id, result.track.id)

    assert len(shots) == 2
    assert shots[0].tipo == ShotType.LETRA
    assert shots[0].texto == "primera linea"
    assert shots[0].orden == 1
    assert shots[1].duracion_estimada_seg == 3.0
    assert "primera linea" in shots[0].prompt_imagen


def test_generate_shots_raises_without_lyrics(tmp_path, repository):
    result = CreateTrackProjectUseCase(repository, tmp_path, FakeMediaProbe()).execute(
        name="Empty Test", kind="lyrics_video", audio_bytes=b"x", audio_filename="x.mp3"
    )
    with pytest.raises(ValueError, match="letra"):
        GenerateShotsFromLyricsUseCase(repository).execute(result.chapter.id, result.track.id)
