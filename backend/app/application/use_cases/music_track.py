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

from app.adapters.outbound.storage.cast_writer import write_escenarios_json, write_personajes_json
from app.adapters.outbound.storage.llm_json import extract_json
from app.application.ports.media_probe import MediaProbePort
from app.application.ports.music_analysis import MusicAnalysisPort
from app.application.ports.repository import ProjectRepositoryPort
from app.application.ports.text_generation import TextGenerationPort, TextGenerationRequest
from app.application.ports.transcription import TranscriptionPort
from app.application.use_cases.chapter_editing import CreateChapterUseCase
from app.application.use_cases.story_generation import CastGenerationResult
from app.domain.music.entities import LyricLine, LyricWord, Track
from app.domain.shared.value_objects import ProjectKind, ShotType, Tone
from app.domain.story.entities import Chapter, Character, Location, Project, Shot
from app.prompts.music_cast import MusicCastBrief, build_music_cast_prompt

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
                start_seg=line.start,
            )
            for i, line in enumerate(sorted(lines, key=lambda l: l.start), start=1)
        ]
        self._repository.replace_shots(chapter_id, shots)
        return shots


class GenerateMusicCastUseCase:
    """Elenco visual para el VIDEOCLIP MUSICAL ANIMADO (fase 5) -- version de
    GenerateCastUseCase (fase 1) que parte de la letra transcrita en vez de
    un canon, porque un proyecto de musica no tiene canon. Duplica el
    mapeo JSON->Character/Location de proposito: las precondiciones son
    genuinamente distintas (letra vs. canon+temporada), forzarlas a una
    sola funcion las acoplaria sin necesidad real."""

    def __init__(self, repository: ProjectRepositoryPort, text_port: TextGenerationPort) -> None:
        self._repository = repository
        self._text_port = text_port

    async def execute(self, track_id: str, brief: MusicCastBrief) -> CastGenerationResult:
        track = self._repository.get_track(track_id)
        if track is None:
            raise ValueError(f"Pista no encontrada: {track_id}")
        project = self._repository.get_project(track.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {track.project_id}")
        lines = self._repository.list_lyric_lines(track_id)
        if not lines:
            raise ValueError("Esta pista todavia no tiene letra transcrita -- transcribila primero")

        lyrics_text = "\n".join(line.text for line in sorted(lines, key=lambda l: l.start))
        system, user = build_music_cast_prompt(lyrics_text, brief)
        result = await self._text_port.generate(
            TextGenerationRequest(prompt=user, system=system, max_tokens=4000, temperature=0.9, json_mode=True)
        )
        try:
            data = extract_json(result.text)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"El modelo no devolvio JSON valido para el cast del videoclip: {exc}\n\nRespuesta cruda:\n{result.text[:2000]}"
            ) from exc

        characters: list[Character] = []
        for raw in data.get("personajes", []):
            slug = raw.get("id") or _slugify(raw.get("nombre", "personaje"))
            tokens = {
                "descripcion_corta": raw.get("descripcion_corta", ""),
                "cabello": raw.get("cabello", ""),
                "ojos": raw.get("ojos", ""),
                "marca_distintiva": raw.get("marca_distintiva", ""),
                "atuendo_base": raw.get("atuendo_base", ""),
                "prompt_anchor": raw.get("prompt_anchor", ""),
            }
            character = Character(
                id=str(uuid.uuid4()), project_id=project.id, slug=slug, nombre=raw.get("nombre", slug),
                rol=raw.get("rol", "protagonista"), prompt_anchor=tokens["prompt_anchor"], tokens_visuales=tokens,
            )
            self._repository.save_character(character)
            characters.append(character)

        locations: list[Location] = []
        for raw in data.get("escenarios", []):
            slug = raw.get("id") or _slugify(raw.get("nombre", "escenario"))
            location = Location(
                id=str(uuid.uuid4()), project_id=project.id, slug=slug,
                nombre=raw.get("nombre", slug), descripcion_fija=raw.get("descripcion_fija", ""),
            )
            self._repository.save_location(location)
            locations.append(location)

        write_personajes_json(project.root_path, project.slug, characters)
        write_escenarios_json(project.root_path, project.slug, locations)
        return CastGenerationResult(characters=characters, locations=locations)


_CAMERA_CYCLE = ("zoom in lento", "pan derecha", "zoom out lento", "pan izquierda", "estatico")


class GenerateMusicVideoShotsUseCase:
    """Ventanas de ~8s "cortadas en el beat" (seccion 7 del doc de
    arquitectura, fase 5) en vez de una linea = un shot -- a diferencia de
    LyricsVideo/Karaoke, ESTE producto no muestra letra en pantalla, asi que
    el corte no tiene que respetar limites de linea, solo el ritmo de la
    cancion. Requiere que el cast (GenerateMusicCastUseCase) ya exista para
    que las imagenes salgan con personaje/escenario consistentes -- si
    todavia no hay cast, los shots salen sin personaje/escenario asignado
    (igual generan una imagen, solo que sin anclaje de identidad)."""

    def __init__(self, repository: ProjectRepositoryPort, music_analysis_port: MusicAnalysisPort) -> None:
        self._repository = repository
        self._music_analysis_port = music_analysis_port

    async def execute(self, chapter_id: str, track_id: str, *, window_seconds: float = 8.0) -> list[Shot]:
        track = self._repository.get_track(track_id)
        if track is None:
            raise ValueError(f"Pista no encontrada: {track_id}")
        project = self._repository.get_project(track.project_id)
        if project is None:
            raise ValueError(f"Proyecto no encontrado: {track.project_id}")
        lines = sorted(self._repository.list_lyric_lines(track_id), key=lambda l: l.start)
        characters = self._repository.list_characters(project.id)
        locations = self._repository.list_locations(project.id)

        total_duration = track.duration_seconds
        if total_duration is None:
            total_duration = lines[-1].end if lines else window_seconds
        if not total_duration or total_duration <= 0:
            raise ValueError("No se pudo determinar la duracion de la pista")

        analysis = await self._music_analysis_port.analyze(Path(track.source_path))
        beats = sorted(analysis.beats)

        windows = _build_beat_aligned_windows(total_duration, window_seconds, beats)
        character_slugs = [c.slug for c in characters]
        location_slug = locations[0].slug if locations else None

        shots: list[Shot] = []
        for i, (start, end) in enumerate(windows, start=1):
            overlapping = [l.text for l in lines if l.start < end and l.end > start]
            content_hint = " ".join(overlapping).strip()
            if content_hint:
                tipo = ShotType.LETRA
                prompt_imagen = (
                    f"Cinematic music video shot capturing the mood of: {_paraphrase_hint(content_hint)}. "
                    "Dynamic pose, expressive performance, dramatic lighting, no readable text or captions."
                )
            else:
                tipo = ShotType.INSTRUMENTAL
                prompt_imagen = (
                    "Cinematic instrumental interlude shot, atmospheric mood matching the song's energy, "
                    "dynamic camera composition, no readable text or captions."
                )
            shots.append(
                Shot(
                    id=str(uuid.uuid4()),
                    chapter_id=chapter_id,
                    orden=i,
                    tipo=tipo,
                    personaje_ids=list(character_slugs),
                    escenario_id=location_slug,
                    texto=content_hint,
                    prompt_imagen=prompt_imagen,
                    movimiento_camara=_CAMERA_CYCLE[i % len(_CAMERA_CYCLE)],
                    duracion_estimada_seg=round(end - start, 3),
                    start_seg=round(start, 3),
                )
            )

        self._repository.replace_shots(chapter_id, shots)
        return shots


def _build_beat_aligned_windows(total_duration: float, window_seconds: float, beats: list[float]) -> list[tuple[float, float]]:
    """Arranca cada ventana en ~`window_seconds` desde el inicio de la
    anterior, pero ajusta el corte al beat mas cercano dentro de +-1.5s si
    hay datos de beat reales -- si no (analisis fallido, o el archivo no
    tenia beats detectables), cae a ventanas fijas."""
    tolerance = 1.5
    windows: list[tuple[float, float]] = []
    start = 0.0
    while start < total_duration - 0.5:
        raw_end = min(start + window_seconds, total_duration)
        end = raw_end
        if beats and raw_end < total_duration:
            candidates = [b for b in beats if abs(b - raw_end) <= tolerance and b > start]
            if candidates:
                end = min(candidates, key=lambda b: abs(b - raw_end))
        end = min(max(end, start + 1.0), total_duration)
        windows.append((start, end))
        start = end
    return windows
