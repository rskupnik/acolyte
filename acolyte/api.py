from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from . import jobs
from .registry import get_scraper

app = FastAPI(title="acolyte", version="0.2.0")

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

class ScrapeIn(BaseModel):
    script_id: str = Field(..., examples=["example"])
    webhook_url: Optional[HttpUrl] = None
    args: Optional[Dict[str, Any]] = None

class ScrapeAccepted(BaseModel):
    accepted: bool
    job_id: str

@app.post("/scrape", response_model=ScrapeAccepted, status_code=202)
async def scrape(payload: ScrapeIn = Body(...)) -> ScrapeAccepted:
    runner = get_scraper(payload.script_id)
    if not runner:
        raise HTTPException(status_code=404, detail="unknown script_id")

    webhook = str(payload.webhook_url) if payload.webhook_url else None

    job = jobs.create_job(payload.script_id, webhook)
    args = payload.args or {}

    import asyncio
    asyncio.create_task(jobs.run_job(job, runner, args))
    return ScrapeAccepted(accepted=True, job_id=job.job_id)

@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="unknown job_id")
    return job.to_dict()
