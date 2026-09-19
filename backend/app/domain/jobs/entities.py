"""Job: unidad de trabajo asincrono para toda generacion de IA.

Los casos de uso de generacion (imagen/audio/video por shot, fase 2) nunca
llaman un adaptador de proveedor directamente y esperan la respuesta HTTP --
encolan un Job via JobQueuePort (adapters/outbound/jobs/in_process_job_queue.py)
que lo corre en background y lo persiste, para que el cliente pueda hacer
polling de progreso en vez de bloquear la request."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.shared.value_objects import JobStatus


@dataclass
class Job:
    id: str
    project_id: str | None
    kind: str  # ej. "generate_shot_image", "generate_shot_audio", "generate_shot_video"
    provider: str
    shot_id: str | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    payload: dict = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None
    cost_estimate: float | None = None
    cost_actual: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
