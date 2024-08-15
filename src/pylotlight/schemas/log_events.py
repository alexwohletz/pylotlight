from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Union, Dict, Any, Literal
from pydantic.json import pydantic_encoder

class LogEventBase(BaseModel):
    timestamp: datetime = Field(..., description="The timestamp of the log event")
    source: str = Field(..., description="The source of the log (e.g., 'airflow', 'dbt')")
    status_type: str = Field(..., description="The status type of the log event (e.g., 'outage', 'incident','failure','normal')")
    log_level: str = Field(..., description="The log level (e.g., INFO, ERROR)")
    message: str = Field(..., description="The log message")

    model_config = {
        "json_encoders": {datetime: pydantic_encoder},
        "protected_namespaces": ()
    }

class AirflowHealthCheckEvent(LogEventBase):
    source: Literal["airflow_health_check"]
    metadatabase_status: str
    scheduler_status: str
    triggerer_status: str

class AirflowImportErrorEvent(LogEventBase):
    source: Literal["airflow_import_error"]
    filename: str
    stack_trace: str

class AirflowFailedDagEvent(LogEventBase):
    source: Literal["airflow_failed_dag"]
    dag_id: str
    execution_date: datetime
    try_number: int

class DbtLogEvent(LogEventBase):
    source: Literal["dbt"]
    model_name: Optional[str] = None
    node_id: Optional[str] = None
    run_id: Optional[str] = None

class GenericLogEvent(LogEventBase):
    additional_data: Dict[str, Any] = Field(default_factory=dict)

LogEvent = Union[AirflowHealthCheckEvent, AirflowImportErrorEvent, AirflowFailedDagEvent, DbtLogEvent, GenericLogEvent]

# API-specific models
class LogIngestionRequest(BaseModel):
    log_event: LogEvent

    model_config = {
        "protected_namespaces": ()
    }

class BatchLogIngestionRequest(BaseModel):
    log_events: List[LogEvent]

    model_config = {
        "protected_namespaces": ()
    }

class LogIngestionResponse(BaseModel):
    success: bool
    message: str
    event_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    model_config = {
        "protected_namespaces": ()
    }
    
class BatchLogIngestionResponse(BaseModel):
    success: bool
    message: str
    event_ids: List[str]
    failed_events: List[int] = Field(default_factory=list, description="Indices of failed events in the batch")

    model_config = {
        "protected_namespaces": ()
    }

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogRetrievalRequest(BaseModel):
    source: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    log_level: Optional[LogLevel] = None
    filters: Dict[str, Any] = Field(default_factory=dict, description="Source-specific filters")
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)

    model_config = {
        "protected_namespaces": ()
    }

class LogRetrievalResponse(BaseModel):
    logs: List[LogEvent]
    total_count: int
    has_more: bool

    model_config = {
        "protected_namespaces": ()
    }

# SSE-specific model
class SSEMessage(BaseModel):
    event: str = Field(..., description="The type of SSE event")
    data: LogEvent = Field(..., description="The log event data")

    model_config = {
        "protected_namespaces": ()
    }