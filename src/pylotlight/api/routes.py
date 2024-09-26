from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from datetime import datetime
import logging
from sse_starlette.sse import EventSourceResponse
import asyncio
import aioredis
from pydantic import ValidationError
from pylotlight.sources import get_source_handler

from pylotlight.schemas.log_events import (
    LogEvent,
    LogIngestionRequest,
    BatchLogIngestionRequest,
    LogIngestionResponse,
    BatchLogIngestionResponse,
    LogRetrievalResponse,
    LogLevel,
    GenericLogEvent,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Global Redis client
redis = None

async def get_redis():
    global redis
    if redis is None:
        redis = await aioredis.from_url("redis://redis:6379/0")
    return redis

@router.post("/ingest", response_model=LogIngestionResponse)
async def ingest_log(request: LogIngestionRequest):
    warnings = []
    try:
        log_event_dict = request.log_event.model_dump()
        source = log_event_dict.get("source")

        try:
            source_handler = get_source_handler(source)
            log_event = source_handler.validate_and_process(log_event_dict)
        except ValueError as ve:
            warnings.append(str(ve))
            log_event = GenericLogEvent(**log_event_dict)

        log_json = log_event.model_dump_json()
        redis_client = await get_redis()
        event_id = await redis_client.lpush("log_queue", log_json)
        
        # Publish to SSE channel
        await redis_client.publish('sse_channel', log_json)
        
        return LogIngestionResponse(
            success=True,
            message="Log pushed to queue and published to SSE channel",
            event_id=str(event_id),
            warnings=warnings,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest log: {str(e)}")

@router.post("/ingest/batch", response_model=BatchLogIngestionResponse)
async def ingest_log_batch(request: BatchLogIngestionRequest):
    event_ids = []
    failed_events = []
    redis_client = await get_redis()

    for index, log_event in enumerate(request.log_events):
        try:
            log_json = log_event.model_dump_json()
            event_id = await redis_client.lpush("log_queue", log_json)
            await redis_client.publish('sse_channel', log_json)
            event_ids.append(str(event_id))
        except Exception:
            failed_events.append(index)

    success = len(failed_events) == 0
    message = "All logs ingested successfully" if success else f"{len(failed_events)} logs failed to ingest"

    return BatchLogIngestionResponse(
        success=success,
        message=message,
        event_ids=event_ids,
        failed_events=failed_events,
    )

@router.get("/logs", response_model=LogRetrievalResponse)
async def retrieve_logs(
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    log_level: Optional[LogLevel] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    # In a real-world scenario, you would query the database here
    # For this example, we'll just return dummy data
    dummy_log = GenericLogEvent(
        timestamp=datetime.now(),
        source="airflow_health_check",
        status_type="normal",
        log_level="INFO",
        message="This is a dummy log message",
        additional_data={
            "metadatabase_status": "healthy",
            "scheduler_status": "healthy",
            "triggerer_status": "healthy"
        }
    )

    logs = [dummy_log] * min(limit, 10)  # Return at most 10 dummy logs
    total_count = 100  # Dummy total count
    has_more = (offset + limit) < total_count

    return LogRetrievalResponse(logs=logs, total_count=total_count, has_more=has_more)

@router.get('/sse')
async def sse(request: Request):
    async def event_generator():
        redis_client = await get_redis()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('sse_channel')
        logger.info("Subscribed to sse_channel")

        try:
            while True:
                # Wait for a message to be received
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if message is not None:
                    logger.info(f"Received message: {message}")
                    if message['type'] == 'message':
                        try:
                            data = message['data'].decode('utf-8')
                            logger.info(f"Sending SSE event: {data}")
                            yield {
                                "event": "update",
                                "data": data
                            }
                        except Exception as decode_error:
                            logger.error(f"Failed to decode message: {decode_error}")
                await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error in SSE event generator: {str(e)}")
        finally:
            await pubsub.unsubscribe('sse_channel')
            logger.info("Unsubscribed from sse_channel")

    return EventSourceResponse(event_generator())