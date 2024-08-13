from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Union, Dict, Any

class LogEventBase(BaseModel):
    timestamp: datetime = Field(..., description="The timestamp of the log event")
    source: str = Field(..., description="The source of the log (e.g., 'airflow', 'dbt')")
    log_level: str = Field(..., description="The log level (e.g., INFO, ERROR)")
    message: str = Field(..., description="The log message")

class AirflowLogEvent(LogEventBase):
    source: str = Field("airflow", const=True)
    dag_id: str
    task_id: str
    execution_date: datetime
    try_number: int

class DbtLogEvent(LogEventBase):
    source: str = Field("dbt", const=True)
    model_name: Optional[str] = None
    node_id: Optional[str] = None
    run_id: Optional[str] = None

class GenericLogEvent(LogEventBase):
    additional_data: Dict[str, Any] = Field(default_factory=dict)

LogEvent = AirflowLogEvent | DbtLogEvent | GenericLogEvent

# API-specific models
class LogIngestionRequest(BaseModel):
    log_event: LogEvent

class BatchLogIngestionRequest(BaseModel):
    log_events: List[LogEvent]

class LogIngestionResponse(BaseModel):
    success: bool
    message: str
    event_id: Optional[str] = None

class BatchLogIngestionResponse(BaseModel):
    success: bool
    message: str
    event_ids: List[str]
    failed_events: List[int] = Field(default_factory=list, description="Indices of failed events in the batch")

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

class LogRetrievalResponse(BaseModel):
    logs: List[LogEvent]
    total_count: int
    has_more: bool

# SSE-specific model
class SSEMessage(BaseModel):
    event: str = Field(..., description="The type of SSE event")
    data: LogEvent = Field(..., description="The log event data")