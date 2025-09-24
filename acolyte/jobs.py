from __future__ import annotations
import asyncio, time, uuid, json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import httpx

@dataclass
class Job:
    job_id: str
    script_id: str
    status: str               # "running" | "succeeded" | "failed"
    started_at: float
    finished_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    webhook_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["started_at"] = _to_iso(self.started_at)
        d["finished_at"] = _to_iso(self.finished_at) if self.finished_at else None
        d["duration_ms"] = (
            int((self.finished_at - self.started_at) * 1000)
            if self.finished_at else None
        )
        return d

def _to_iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

_JOBS: Dict[str, Job] = {}
_SEMAPHORE = asyncio.Semaphore(4)

def create_job(script_id: str, webhook_url: Optional[str]) -> Job:
    job = Job(
        job_id=uuid.uuid4().hex,
        script_id=script_id,
        status="running",
        started_at=time.time(),
        webhook_url=webhook_url,
    )
    _JOBS[job.job_id] = job
    return job

def get_job(job_id: str) -> Optional[Job]:
    return _JOBS.get(job_id)

async def run_job(job: Job, runner, args: Dict[str, Any]) -> None:
    try:
        async with _SEMAPHORE:
            result = await runner(args)
        job.status = "succeeded"
        job.result = result
    except Exception as e:
        job.status = "failed"
        job.error = repr(e)
    finally:
        job.finished_at = time.time()
        # Fire-and-forget webhook (do not block)
        if job.webhook_url:
            asyncio.create_task(_post_webhook(job))

async def _post_webhook(job: Job) -> None:
    payload = {
        "job_id": job.job_id,
        "script_id": job.script_id,
        "status": job.status,
        "result": job.result,
        "error": job.error,
        "started_at": job.to_dict()["started_at"],
        "finished_at": job.to_dict()["finished_at"],
        "duration_ms": job.to_dict()["duration_ms"],
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            await client.post(job.webhook_url, json=payload)
    except Exception:
        # swallow errors
        pass
