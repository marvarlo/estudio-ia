"""Casos de uso del pipeline de musica (fase 4, seccion 6 del doc de
arquitectura): registrar una pista nueva, transcribirla, editar las lineas
de letra resultantes, y convertirlas en shots -- reutilizando DELIBERADAMENTE
`Chapter`/`Shot` (el propio dominio ya documenta que "en musica el mismo
concepto cubre una ventana de la cancion", ver domain/story/entities.py)
para heredar sin tocarla toda la infraestructura de la fase 2: generacion de
imagen por shot, versionado de assets, cola de jobs, y el sidecar de render
de la fase 3. Cada pista vive en un proyecto con exactamente UN capitulo
(numero 1), invisible para el usuario -- la UI de musica nunca dice
"capitulo".

Alcance de esta fase (decision explicita, ver README): un shot por linea de
letra (opcion valida segun el propio doc de arquitectura, "una por
seccion/linea"), sin deteccion de estructura (BPM/secciones) ni separacion
de fuentes verificada en vivo -- ver DemucsSeparationAdapter."""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.application.ports.media_probe import MediaProbePort
from app.application.ports.repository import ProjectRepositoryPort
from app.application.ports.transcription import TranscriptionPort
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.domain.music.entities import LyricLine, LyricWord, Track
from app.domain.shared.value_objects import ProjectKind, ShotType, Tone
from app.domain.story.entities import Chapter, Project, Shot

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://estudio-ia.local/")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_MUSIC_KINDS = {ProjectKind.MUSIC_VIDEO, ProjectKind.LYRICS_VIDEO, ProjectKind.KARAOKE}


def _paraphrase_hint(text: str) -> str:
    """Evita pasar la letra tal cual entre comillas al generador de imagen
    (ver comentario en GenerateShotsFromLyricsUseCase) -- solo limpia
    puntuacion/mayusculas, no es una paraphrase real por LLM todavia."""
    return text.strip().strip(".,!?¡¿").lower()


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return _SLUG_RE.sub("-", normalized.lower()).strip("-") or "pista"


@dataclass
class TrackProject:
    project: Project
    chapter: Chapter
    track: Track


class CreateTrackProjectUseCase:
    """Crea el proyecto + capitulo unico + Track a partir de un audio ya
    guardado en disco (el router escribe el UploadFile antes de llamar esto,
    igual que un multipart no pertenece a la capa de aplicacion)."""

    def __init__(self, repository: ProjectRepositoryPort, stories_root: Path, media_probe: MediaProbePort) -> None:
        self._repository = repository
        self._stories_root = stories_root
        self._media_probe = media_probe

    def execute(self, name: str, kind: str, audio_bytes: bytes, audio_filename: str) -> TrackProject:
        project_kind = ProjectKind(kind) if kind in ProjectKind._value2member_map_ else ProjectKind.LYRICS_VIDEO
        if project_kind not in _MUSIC_KINDS:
            raise ValueError(f"kind debe ser uno de {sorted(k.value for k in _MUSIC_KINDS)}")

        base_slug = _slugify(name)
        slug = base_slug
        suffix = 2
        while self._repository.get_project_by_slug(slug) is not None:
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        root_path = self._stories_root / slug
        root_path.mkdir(parents=True, exist_ok=True)

        project = Project(
            id=str(uuid.uuid5(_NAMESPACE, f"project/{slug}")),
            slug=slug,
            name=name,
            kind=project_kind,
            root_path=root_path,
            tono=Tone.NORMAL,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.save_project(project)

        chapter = CreateChapterUseCase(self._repository).execute(project.id, titulo=name, numero=1)

        # Misma convencion de carpetas que un capitulo de historia
        # (capitulo-N/assets/...) -- asi el track queda bajo el mismo
        # "public dir" que las imagenes que GenerateShotImageUseCase genera
        # sin cambiarle una linea, y BuildMusicTimelineUseCase puede resolver
        # todo relativo a una sola carpeta (ver render_music_video.py).
        extension = Path(audio_filename).suffix or ".mp3"
        audio_dir = root_path / f"capitulo-{chapter.numero}" / "assets" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"track{extension}"
        audio_path.write_bytes(audio_bytes)

        media_info = self._media_probe.probe(audio_path)
        track = Track(
            id=str(uuid.uuid4()),
            project_id=project.id,
            source_path=str(audio_path),
            duration_seconds=media_info.duration_seconds,
        )
        self._repository.save_track(track)

        return TrackProject(project=project, chapter=chapter, track=track)


class TranscribeTrackUseCase:
    def __init__(self, repository: ProjectRepositoryPort, transcription_port: TranscriptionPort) -> None:
        self._repository = repository
        self._transcription_port = transcription_port

    async def execute(self, track_id: str, *, language: str | None = None) -> list[LyricLine]:
        track = self._repository.get_track(track_id)
        if track is None:
            raise ValueError(f"Pista no encontrada: {track_id}")

        result = await self._transcription_port.transcribe(Path(track.source_path), language=language)

        lines = _words_to_lines(track_id, result.words)
        self._repository.replace_lyric_lines(track_id, lines)
        return lines


def _words_to_lines(track_id: str, words: list) -> list[LyricLine]:
    """Reconstruye lineas a partir de la lista plana de palabras -- una linea
    nueva cada vez que hay un salto de mas de 1.2s entre el fin de una
    palabra y el inicio de la siguiente (silencio real, no solo el espacio
    entre palabras), o cada 12 palabras si nunca hay pausas (verso corrido).
    Simplificacion deliberada respecto al re-bucketing a 8s del skill
    original: la duracion real de CADA linea la fija el propio timestamp, no
    una ventana fija -- ver seccion 6 del doc de arquitectura."""
    if not words:
        return []

    lines: list[LyricLine] = []
    current: list = []
    index = 0

    def flush() -> None:
        nonlocal index, current
        if not current:
            return
        line_words = [LyricWord(text=w.text, start=w.start, end=w.end, confidence=w.probability, suspect=w.suspect) for w in current]
        lines.append(
            LyricLine(
                id=str(uuid.uuid4()),
                track_id=track_id,
                index=index,
                text=" ".join(w.text for w in current).strip(),
                start=current[0].start,
                end=current[-1].end,
                words=line_words,
            )
        )
        index += 1
        current = []

    for word in words:
        if current and (word.start - current[-1].end > 1.2 or len(current) >= 12):
            flush()
        current.append(word)
    flush()
    return lines


class UpdateLyricLineUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, line_id: str, *, text: str, start: float, end: float) -> LyricLine:
        line = self._repository.get_lyric_line(line_id)
        if line is None:
            raise ValueError(f"Linea no encontrada: {line_id}")
        line.text = text
        line.start = start
        line.end = end
        self._repository.save_lyric_line(line)
        return line


class DeleteLyricLineUseCase:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, line_id: str) -> None:
        self._repository.delete_lyric_line(line_id)


class GenerateShotsFromLyricsUseCase:
    """Convierte cada LyricLine en un Shot (tipo LETRA) del capitulo unico de
    la pista -- reemplaza los shots existentes por completo (llamar de nuevo
    tras editar la letra es la forma esperada de re-generar, no un accidente
    a evitar)."""

    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository

    def execute(self, chapter_id: str, track_id: str) -> list[Shot]:
        lines = self._repository.list_lyric_lines(track_id)
        if not lines:
            raise ValueError("Esta pista todavia no tiene letra transcrita")

        shots = [
            Shot(
                id=str(uuid.uuid4()),
                chapter_id=chapter_id,
                orden=i,
                tipo=ShotType.LETRA,
                texto=line.text,
                # OJO: NO citar la letra entre comillas en el prompt -- verificado en vivo que
                # Flux-2-Klein-4B (Lemonade) toma el texto citado como literal a dibujar en la
                # imagen (aparecio como texto garabateado sobre el fondo) incluso con
                # "no readable text" en la misma frase y NEGATIVE_PROMPT pidiendo evitar "text".
                # Describir el mood en tercera persona sin comillas evita el problema.
                prompt_imagen=(
                    f"Atmospheric cinematic background scene evoking the mood of: {_paraphrase_hint(line.text)}. "
                    "Absolutely no readable text, letters, words, captions, subtitles, logos, or watermarks "
                    "anywhere in the image -- a pure background visual, no signage of any kind. "
                    "Mood lighting, painterly, no characters unless clearly implied."
                ),
                duracion_estimada_seg=max(line.end - line.start, 1.0),
            )
            for i, line in enumerate(sorted(lines, key=lambda l: l.start), start=1)
        ]
        self._repository.replace_shots(chapter_id, shots)
        return shots
