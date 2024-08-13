from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid

app = FastAPI()

class LogSource(str, Enum):
    DBT = "dbt"
    AIRFLOW = "airflow"
    CUSTOM = "custom"

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class BaseLogEvent(BaseModel):
    source: LogSource
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel
    message: str
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class DbtLogEvent(BaseLogEvent):
    source: LogSource = LogSource.DBT
    dbt_info: Dict[str, Any]
    node_info: Optional[Dict[str, Any]]

class AirflowLogEvent(BaseLogEvent):
    source: LogSource = LogSource.AIRFLOW
    dag_id: str
    task_id: str
    execution_date: datetime

class CustomLogEvent(BaseLogEvent):
    source: LogSource = LogSource.CUSTOM
    custom_data: Dict[str, Any]

@app.post("/ingest_log")
async def ingest_log(log_event: Dict[str, Any]):
    try:
        source = LogSource(log_event.get("source", "custom"))
        if source == LogSource.DBT:
            event = DbtLogEvent(**log_event)
        elif source == LogSource.AIRFLOW:
            event = AirflowLogEvent(**log_event)
        else:
            event = CustomLogEvent(**log_event)
        
        # Here you would typically save the event to a database or message queue
        # For this example, we'll just print it
        print(f"Received log event: {event.model_dump_json()}")
        
        return {"status": "success", "event_id": event.event_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid log event: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)