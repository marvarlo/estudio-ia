"""Job: unidad de trabajo asincrono para toda generacion de IA.

Los casos de uso nunca llaman un adaptador de proveedor directamente para una
operacion larga -- encolan un Job y el ejecutor (fase posterior a esta) lo
procesa. Fase 0 solo persiste jobs sincronicamente (ver
application/use_cases/test_provider.py), sin cola real todavia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.shared.value_objects import JobStatus


@dataclass
class Job:
    id: str
    project_id: str | None
    kind: str  # ej. "generate_shot_image", "provider_health_check"
    provider: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    payload: dict = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None
    cost_estimate: float | None = None
    cost_actual: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
