from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime

router = APIRouter()

class LogEvent(BaseModel):
    source: str
    timestamp: datetime
    data: Dict[str, Any]

log_events: List[LogEvent] = []

@router.post("/ingest_log")
async def ingest_log(event: LogEvent):
    log_events.append(event)
    return {"status": "success", "message": "Log event ingested"}

@router.get("/events")
async def get_events():
    return log_events