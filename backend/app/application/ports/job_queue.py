"""Puerto: encolar/consultar/cancelar Jobs. Fase 0 usa un ejecutor en proceso
(ver adapters/outbound/repository para persistencia); este puerto es lo que
permite migrar a Huey/arq despues sin tocar casos de uso."""
from __future__ import annotations

from typing import Awaitable, Callable, Protocol

from app.domain.jobs.entities import Job


class JobQueuePort(Protocol):
    async def enqueue(self, job: Job, run: Callable[[], Awaitable[dict]]) -> Job: ...
    async def get(self, job_id: str) -> Job | None: ...
    async def cancel(self, job_id: str) -> bool: ...
