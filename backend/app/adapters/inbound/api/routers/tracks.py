from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.adapters.inbound.api.deps import (
    get_job_queue,
    get_media_probe,
    get_music_analysis_port,
    get_provider_registry,
    get_render_port,
    get_repository,
    get_settings,
    resolve_adapter,
)
from app.adapters.inbound.api.schemas import (
    CastGenerationOut,
    JobOut,
    LyricLineOut,
    LyricLineUpdateRequest,
    MusicCastGenerateRequest,
    MusicRenderRequest,
    MusicShotsWindowRequest,
    ShotOut,
    TrackOut,
    TrackProjectOut,
    TranscribeRequest,
)
from app.application.ports.job_queue import JobQueuePort
from app.application.use_cases.music_track import (
    CreateTrackProjectUseCase,
    DeleteLyricLineUseCase,
    GenerateMusicCastUseCase,
    GenerateMusicVideoShotsUseCase,
    GenerateShotsFromLyricsUseCase,
    TrackProject,
    TranscribeTrackUseCase,
    UpdateLyricLineUseCase,
)
from app.application.use_cases.render_music_video import RenderMusicVideoUseCase
from app.domain.jobs.entities import Job
from app.prompts.music_cast import MusicCastBrief

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


def _chapter_for_track(repository, track):
    project = repository.get_project(track.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    chapters = repository.list_chapters(project.id)
    if not chapters:
        raise HTTPException(status_code=404, detail="Este track no tiene capitulo asociado")
    return project, chapters[0]


@router.post("", response_model=TrackProjectOut)
async def create_track(
    name: str = Form(...),
    kind: str = Form("lyrics_video"),
    file: UploadFile = File(...),
    repository=Depends(get_repository),
    settings=Depends(get_settings),
    media_probe=Depends(get_media_probe),
) -> TrackProjectOut:
    audio_bytes = await file.read()
    try:
        result = CreateTrackProjectUseCase(repository, settings.stories_root, media_probe).execute(
            name=name, kind=kind, audio_bytes=audio_bytes, audio_filename=file.filename or "track.mp3"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrackProjectOut.from_domain(result)


@router.get("", response_model=list[TrackOut])
def list_tracks(project_id: str = Query(...), repository=Depends(get_repository)) -> list[TrackOut]:
    return [TrackOut.from_domain(t) for t in repository.list_tracks(project_id)]


@router.get("/{track_id}", response_model=TrackProjectOut)
def get_track(track_id: str, repository=Depends(get_repository)) -> TrackProjectOut:
    track = repository.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    project, chapter = _chapter_for_track(repository, track)
    return TrackProjectOut.from_domain(TrackProject(project=project, chapter=chapter, track=track))


@router.post("/{track_id}/transcribe", response_model=JobOut)
async def transcribe_track(
    track_id: str,
    payload: TranscribeRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    track = repository.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    transcription_port = resolve_adapter(registry, payload.provider_id)
    use_case = TranscribeTrackUseCase(repository, transcription_port)

    async def run() -> dict:
        lines = await use_case.execute(track_id, language=payload.language)
        return {"lines_count": len(lines)}

    job = Job(
        id=str(uuid.uuid4()), project_id=track.project_id, kind="transcribe_track",
        provider=payload.provider_id, payload={"track_id": track_id}, cost_estimate=0.0,
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)


@router.get("/{track_id}/lines", response_model=list[LyricLineOut])
def list_lines(track_id: str, repository=Depends(get_repository)) -> list[LyricLineOut]:
    lines = repository.list_lyric_lines(track_id)
    return [LyricLineOut.from_domain(line) for line in lines]


@router.put("/lines/{line_id}", response_model=LyricLineOut)
def update_line(line_id: str, payload: LyricLineUpdateRequest, repository=Depends(get_repository)) -> LyricLineOut:
    try:
        line = UpdateLyricLineUseCase(repository).execute(line_id, text=payload.text, start=payload.start, end=payload.end)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LyricLineOut.from_domain(line)


@router.delete("/lines/{line_id}", status_code=204)
def delete_line(line_id: str, repository=Depends(get_repository)) -> None:
    DeleteLyricLineUseCase(repository).execute(line_id)


@router.post("/{track_id}/shots:generate", response_model=list[ShotOut])
def generate_shots(track_id: str, repository=Depends(get_repository)) -> list[ShotOut]:
    track = repository.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    _project, chapter = _chapter_for_track(repository, track)
    try:
        shots = GenerateShotsFromLyricsUseCase(repository).execute(chapter.id, track_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [ShotOut.from_domain(s) for s in shots]


@router.post("/{track_id}/cast:generate", response_model=CastGenerationOut)
async def generate_music_cast(
    track_id: str,
    payload: MusicCastGenerateRequest,
    repository=Depends(get_repository),
    registry=Depends(get_provider_registry),
) -> CastGenerationOut:
    """Elenco visual para el videoclip animado (fase 5) -- a partir de la
    letra ya transcrita, no de un canon (los proyectos de musica no tienen
    uno). Sincrono, igual que /cast:generate de historias en la fase 1."""
    text_port = resolve_adapter(registry, payload.provider_id)
    brief = MusicCastBrief(estilo_visual=payload.estilo_visual, notas=payload.notas)
    try:
        result = await GenerateMusicCastUseCase(repository, text_port).execute(track_id, brief)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CastGenerationOut.from_domain(result)


@router.post("/{track_id}/shots:generate-windows", response_model=list[ShotOut])
async def generate_music_video_shots(
    track_id: str,
    payload: MusicShotsWindowRequest,
    repository=Depends(get_repository),
    music_analysis_port=Depends(get_music_analysis_port),
) -> list[ShotOut]:
    """Ventanas de ~8s cortadas en el beat (videoclip animado, fase 5) --
    distinto de /shots:generate (una linea = un shot, usado por lyrics/
    karaoke): este no muestra letra en pantalla, asi que el corte sigue el
    ritmo de la cancion, no los limites de linea."""
    track = repository.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    _project, chapter = _chapter_for_track(repository, track)
    try:
        shots = await GenerateMusicVideoShotsUseCase(repository, music_analysis_port).execute(
            chapter.id, track_id, window_seconds=payload.window_seconds
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [ShotOut.from_domain(s) for s in shots]


@router.post("/{track_id}/render:generate", response_model=JobOut)
async def render_music_video(
    track_id: str,
    payload: MusicRenderRequest,
    repository=Depends(get_repository),
    render_port=Depends(get_render_port),
    media_probe=Depends(get_media_probe),
    queue: JobQueuePort = Depends(get_job_queue),
) -> JobOut:
    track = repository.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Pista no encontrada")
    _project, chapter = _chapter_for_track(repository, track)
    use_case = RenderMusicVideoUseCase(repository, render_port, media_probe)

    async def run() -> dict:
        asset = await use_case.execute(chapter.id, track_id, payload.composition_id)
        return {"asset_id": asset.id, "path": str(asset.path)}

    job = Job(
        id=str(uuid.uuid4()), project_id=track.project_id, kind="render_music_video",
        provider="remotion", payload={"track_id": track_id, "composition_id": payload.composition_id}, cost_estimate=0.0,
    )
    job = await queue.enqueue(job, run)
    return JobOut.from_domain(job)
