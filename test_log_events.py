import random
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust this to your pylotlight API URL
INGEST_ENDPOINT = f"{BASE_URL}/ingest"
BATCH_INGEST_ENDPOINT = f"{BASE_URL}/ingest/batch"
NUM_EVENTS = 10
INTERVAL = 2  # seconds between events

# Sample data
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
SOURCES = ["airflow", "dbt", "generic"]
SOURCE_TYPES = {
    "airflow": ["health_check", "import_error", "failed_dag"],
    "dbt": ["dbt"],
    "generic": ["generic"]
}
STATUS_TYPE_MAPPING = {
    "health_check": "normal",
    "import_error": "incident",
    "failed_dag": "failure",
    "dbt": "normal",
    "generic": lambda: random.choice(["outage", "incident", "failure", "normal"]),
}
LOG_LEVEL_MAPPING = {
    "incident": "ERROR",
    "failure": "CRITICAL",
    "outage": "WARNING",
    "normal": "INFO",
}

def generate_base_log_event(source: str, source_type: str) -> Dict[str, Any]:
    status_type = STATUS_TYPE_MAPPING[source_type]
    if callable(status_type):
        status_type = status_type()
    log_level = LOG_LEVEL_MAPPING.get(status_type, random.choice(LOG_LEVELS))

    return {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "source_type": source_type,
        "status_type": status_type,
        "log_level": log_level,
        "message": f"{status_type.upper()} event for {source} ({source_type})",
    }

def generate_airflow_health_check_event() -> Dict[str, Any]:
    event = generate_base_log_event("airflow", "health_check")
    event.update({
        "metadatabase_status": random.choice(["healthy", "unhealthy"]),
        "scheduler_status": random.choice(["healthy", "unhealthy"]),
        "triggerer_status": random.choice(["healthy", "unhealthy"])
    })
    return event

def generate_airflow_import_error_event() -> Dict[str, Any]:
    event = generate_base_log_event("airflow", "import_error")
    event.update({
        "filename": f"/path/to/dag/file_{random.randint(1, 100)}.py",
        "stack_trace": f"ImportError: No module named 'missing_module_{random.randint(1, 10)}'"
    })
    return event

def generate_airflow_failed_dag_event() -> Dict[str, Any]:
    event = generate_base_log_event("airflow", "failed_dag")
    event.update({
        "dag_id": f"example_dag_{random.randint(1, 50)}",
        "execution_date": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
        "try_number": random.randint(1, 3)
    })
    return event

def generate_dbt_log_event() -> Dict[str, Any]:
    event = generate_base_log_event("dbt", "dbt")
    event.update({
        "model_name": f"model_{random.randint(1, 100)}",
        "node_id": f"model.example.model_{random.randint(1, 100)}",
        "run_id": f"run_{random.randint(1000, 9999)}"
    })
    return event

def generate_generic_log_event() -> Dict[str, Any]:
    event = generate_base_log_event("generic", "generic")
    event.update({
        "additional_data": {
            "key1": f"value_{random.randint(1, 100)}",
            "key2": random.random(),
            "key3": random.choice([True, False])
        }
    })
    return event

def generate_log_event() -> Dict[str, Any]:
    source = random.choice(SOURCES)
    source_type = random.choice(SOURCE_TYPES[source])
    
    if source == "airflow":
        if source_type == "airflow_":
            return generate_airflow_health_check_event()
        elif source_type == "import_error":
            return generate_airflow_import_error_event()
        elif source_type == "failed_dag":
            return generate_airflow_failed_dag_event()
    elif source == "dbt":
        return generate_dbt_log_event()
    else:
        return generate_generic_log_event()

def send_log_event(event: Dict[str, Any]) -> None:
    try:
        response = requests.post(INGEST_ENDPOINT, json={"log_event": event})
        response.raise_for_status()
        print(f"Event sent successfully: {event['source']} ({event['source_type']})")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send event: {e}")

def send_batch_log_events(events: List[Dict[str, Any]]) -> None:
    try:
        response = requests.post(BATCH_INGEST_ENDPOINT, json={"log_events": events})
        response.raise_for_status()
        print(f"Batch of {len(events)} events sent successfully")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send batch: {e}")

def main() -> None:
    events = [generate_log_event() for _ in range(NUM_EVENTS)]

    # Option 1: Send events one by one
    for event in events:
        send_log_event(event)
        time.sleep(INTERVAL)

    # Option 2: Send events in batches
    # batch_size = 10
    # for i in range(0, len(events), batch_size):
    #     batch = events[i:i+batch_size]
    #     send_batch_log_events(batch)
    #     time.sleep(INTERVAL)

if __name__ == "__main__":
    main()