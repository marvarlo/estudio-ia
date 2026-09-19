"""Punto de entrada de la API. Crea los singletons (engine, repositorio,
registro de proveedores) en el lifespan y los cuelga de `app.state` -- los
routers los toman via Depends() (ver adapters/inbound/api/deps.py).

Correr con: uv run uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.inbound.api.routers import chapters, jobs, media, projects, providers, sheets, shots, tracks, voice_pool
from app.adapters.outbound.jobs.in_process_job_queue import InProcessJobQueue
from app.adapters.outbound.media.ffprobe_probe import FfprobeMediaProbe
from app.adapters.outbound.render.remotion_render_adapter import RemotionRenderAdapter
from app.adapters.outbound.repository.db import create_db_and_tables, make_engine
from app.adapters.outbound.repository.project_repository import SqlProjectRepository
from app.config.provider_registry import ProviderRegistry
from app.config.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.load()
    engine = make_engine(settings)
    create_db_and_tables(engine)

    app.state.settings = settings
    app.state.engine = engine
    app.state.repository = SqlProjectRepository(engine)
    app.state.provider_registry = ProviderRegistry(settings)
    app.state.job_queue = InProcessJobQueue(app.state.repository)
    app.state.media_probe = FfprobeMediaProbe()
    app.state.render_port = RemotionRenderAdapter(settings.render_project_dir, app.state.media_probe)

    yield


app = FastAPI(title="Estudio IA", version="0.1.0", lifespan=lifespan)

# El frontend (Vite) corre en otro puerto durante desarrollo -- sin esto el
# navegador bloquea las llamadas fetch por CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(chapters.router)
app.include_router(shots.router)
app.include_router(voice_pool.router)
app.include_router(sheets.router)
app.include_router(tracks.router)
app.include_router(jobs.router)
app.include_router(providers.router)
app.include_router(media.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
