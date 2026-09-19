import asyncio

import pytest

from app.adapters.outbound.jobs.in_process_job_queue import InProcessJobQueue
from app.domain.jobs.entities import Job
from app.domain.shared.value_objects import JobStatus


async def _wait_until_terminal(queue: InProcessJobQueue, job_id: str, timeout: float = 2.0) -> Job:
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        job = await queue.get(job_id)
        if job.status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED):
            return job
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"Job {job_id} no termino a tiempo (status={job.status})")
        await asyncio.sleep(0.01)


async def test_enqueue_runs_and_marks_done_with_result(repository):
    queue = InProcessJobQueue(repository)
    job = Job(id="job-1", project_id=None, shot_id=None, kind="test", provider="fake")

    async def run() -> dict:
        return {"ok": True}

    await queue.enqueue(job, run)
    finished = await _wait_until_terminal(queue, "job-1")

    assert finished.status == JobStatus.DONE
    assert finished.result == {"ok": True}
    assert finished.progress == 1.0


async def test_enqueue_marks_failed_with_error_message(repository):
    queue = InProcessJobQueue(repository)
    job = Job(id="job-2", project_id=None, shot_id=None, kind="test", provider="fake")

    async def run() -> dict:
        raise RuntimeError("algo salio mal")

    await queue.enqueue(job, run)
    finished = await _wait_until_terminal(queue, "job-2")

    assert finished.status == JobStatus.FAILED
    assert "algo salio mal" in finished.error


async def test_job_is_persisted_and_gettable_by_id(repository):
    queue = InProcessJobQueue(repository)
    job = Job(id="job-3", project_id="proj-1", shot_id="shot-1", kind="test", provider="fake", cost_estimate=0.02)

    async def run() -> dict:
        return {}

    returned = await queue.enqueue(job, run)
    assert returned.status == JobStatus.PENDING

    await _wait_until_terminal(queue, "job-3")
    stored = repository.get_job("job-3")
    assert stored is not None
    assert stored.project_id == "proj-1"
    assert stored.shot_id == "shot-1"
    assert stored.cost_estimate == 0.02


async def test_cancel_before_completion(repository):
    queue = InProcessJobQueue(repository)
    job = Job(id="job-4", project_id=None, shot_id=None, kind="test", provider="fake")

    async def run() -> dict:
        await asyncio.sleep(10)
        return {}

    await queue.enqueue(job, run)
    await asyncio.sleep(0)  # deja que el task arranque y llegue al sleep(10) antes de cancelarlo
    cancelled = await queue.cancel("job-4")
    assert cancelled is True

    finished = await _wait_until_terminal(queue, "job-4")
    assert finished.status == JobStatus.CANCELLED


async def test_cancel_unknown_job_returns_false(repository):
    queue = InProcessJobQueue(repository)
    assert await queue.cancel("no-existe") is False
