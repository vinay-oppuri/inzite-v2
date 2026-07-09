from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.app.worker import enqueue_research_run, get_research_run, run_research_now
from src.core.schemas import ResearchRunRecord

router = APIRouter(prefix="/research", tags=["research"])
logger = logging.getLogger(__name__)


class ResearchRequest(BaseModel):
    idea: str = Field(min_length=1)


@router.post("", response_model=ResearchRunRecord, status_code=202)
async def create_research_run(payload: ResearchRequest) -> ResearchRunRecord:
    """Enqueue a research run and return immediately."""
    logger.info("Received async research request")
    return enqueue_research_run(payload.idea)


@router.post("/sync", response_model=ResearchRunRecord)
async def run_research_sync(payload: ResearchRequest) -> ResearchRunRecord:
    """Run the graph inline and return the completed run record."""
    logger.info("Received sync research request")
    return await run_research_now(payload.idea)


@router.get("/{run_id}", response_model=ResearchRunRecord)
async def read_research_run(run_id: str) -> ResearchRunRecord:
    logger.info("Reading research run %s", run_id)
    record = get_research_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="research run not found")
    return record


@router.get("/{run_id}/events")
async def stream_research_run(run_id: str) -> StreamingResponse:
    logger.info("Streaming research run %s", run_id)
    if get_research_run(run_id) is None:
        raise HTTPException(status_code=404, detail="research run not found")

    async def events():
        logger.debug("Opening event stream for run %s", run_id)
        last_payload = ""
        while True:
            record = get_research_run(run_id)
            if record is None:
                break
            payload = record.model_dump_json()
            if payload != last_payload:
                yield f"event: status\ndata: {payload}\n\n"
                last_payload = payload
            if record.status in {"completed", "failed"}:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream")
