"""Implementacion de JobQueuePort para la fase 2: un ejecutor asyncio EN
PROCESO (seccion 8 del doc de arquitectura, "fase inicial: ejecutor asyncio
en el mismo proceso, con tabla jobs en SQLite"). El puerto existe para poder
migrar a Huey/arq sin tocar los casos de uso el dia que esto se vuelva un
cuello de botella (varios usuarios, o jobs que deban sobrevivir un reinicio
del proceso) -- no antes.

Limitacion conocida y aceptada para esta fase: un Job en estado RUNNING
cuando el proceso de uvicorn se reinicia queda huerfano (nunca se marca
FAILED) -- no hay recuperacion tras crash todavia."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.application.ports.repository import ProjectRepositoryPort
from app.domain.jobs.entities import Job
from app.domain.shared.value_objects import JobStatus


class InProcessJobQueue:
    def __init__(self, repository: ProjectRepositoryPort) -> None:
        self._repository = repository
        self._tasks: dict[str, asyncio.Task] = {}

    async def enqueue(self, job: Job, run: Callable[[], Awaitable[dict]]) -> Job:
        now = datetime.now(timezone.utc)
        job.status = JobStatus.PENDING
        job.created_at = job.created_at or now
        job.updated_at = now
        self._repository.save_job(job)

        async def _runner() -> None:
            job.status = JobStatus.RUNNING
            job.updated_at = datetime.now(timezone.utc)
            self._repository.save_job(job)
            try:
                result = await run()
                job.status = JobStatus.DONE
                job.progress = 1.0
                job.result = result
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                raise
            except Exception as exc:  # noqa: BLE001 - un job fallido se reporta, no tumba el proceso
                job.status = JobStatus.FAILED
                # str(exc) puede venir vacio (ej. httpx.ReadTimeout no lleva
                # mensaje) -- verificado en vivo con una derivacion de hoja
                # de produccion que superó el timeout del LLM local y dejo
                # error="" en vez de algo util. Cae al nombre de la clase
                # para que el job siempre tenga un motivo legible.
                job.error = str(exc) or type(exc).__name__
            finally:
                job.updated_at = datetime.now(timezone.utc)
                self._repository.save_job(job)
                self._tasks.pop(job.id, None)

        self._tasks[job.id] = asyncio.create_task(_runner())
        return job

    async def get(self, job_id: str) -> Job | None:
        return self._repository.get_job(job_id)

    async def cancel(self, job_id: str) -> bool:
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        return task.cancel()
