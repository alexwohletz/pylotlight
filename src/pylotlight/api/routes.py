from fastapi import APIRouter, HTTPException, Query
from redis import Redis
from typing import List, Optional
from datetime import datetime
from pylotlight.schemas.log_events import (
    LogEvent,
    LogIngestionRequest,
    BatchLogIngestionRequest,
    LogIngestionResponse,
    BatchLogIngestionResponse,
    LogRetrievalResponse,
    LogLevel,
    AirflowHealthCheckEvent,
    AirflowImportErrorEvent,
    AirflowFailedDagEvent,
    DbtLogEvent,
    GenericLogEvent,
)
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
import logging

router = APIRouter()

redis_client = Redis(host="redis", port=6379, db=0)
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=LogIngestionResponse)
async def ingest_log(request: LogIngestionRequest):
    warnings = []
    try:
        logger.debug(f"Received log event: {request.log_event}")

        # Use model_dump() instead of dict()
        log_event_dict = request.log_event.model_dump()
        source = log_event_dict.get("source")

        if source.startswith("airflow_"):
            try:
                if source == "airflow_health_check":
                    log_event = AirflowHealthCheckEvent(**log_event_dict)
                elif source == "airflow_import_error":
                    log_event = AirflowImportErrorEvent(**log_event_dict)
                elif source == "airflow_failed_dag":
                    log_event = AirflowFailedDagEvent(**log_event_dict)
                else:
                    raise ValidationError("Unknown Airflow event type")
            except ValidationError:
                warnings.append(
                    f"Log event doesn't meet {source} requirements, treating as GenericLogEvent"
                )
                log_event = GenericLogEvent(**log_event_dict)
        elif source == "dbt":
            try:
                log_event = DbtLogEvent(**log_event_dict)
            except ValidationError:
                warnings.append(
                    "Log event doesn't meet dbt requirements, treating as GenericLogEvent"
                )
                log_event = GenericLogEvent(**log_event_dict)
        else:
            log_event = GenericLogEvent(**log_event_dict)

        # Use model_dump_json() instead of json()
        log_json = log_event.model_dump_json()
        event_id = redis_client.lpush("log_queue", log_json)
        return LogIngestionResponse(
            success=True,
            message="Log pushed to queue",
            event_id=str(event_id),
            warnings=warnings,
        )
    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(
            status_code=400, detail=f"Invalid log event data: {str(ve)}"
        )
    except Exception as e:
        logger.error(f"Error ingesting log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest log: {str(e)}")


@router.post("/ingest/batch", response_model=BatchLogIngestionResponse)
async def ingest_log_batch(request: BatchLogIngestionRequest):
    event_ids = []
    failed_events = []

    for index, log_event in enumerate(request.log_events):
        try:
            log_json = log_event.model_dump_json()
            event_id = redis_client.lpush("log_queue", log_json)
            event_ids.append(str(event_id))
        except Exception:
            failed_events.append(index)

    success = len(failed_events) == 0
    message = (
        "All logs ingested successfully"
        if success
        else f"{len(failed_events)} logs failed to ingest"
    )

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
