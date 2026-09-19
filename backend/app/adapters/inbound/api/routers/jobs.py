from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.inbound.api.deps import get_job_queue
from app.adapters.inbound.api.schemas import JobOut
from app.application.ports.job_queue import JobQueuePort

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, queue: JobQueuePort = Depends(get_job_queue)) -> JobOut:
    job = await queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return JobOut.from_domain(job)
