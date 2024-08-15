import random
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Union

# Configuration
BASE_URL = "http://localhost:8000"  # Adjust this to your pylotlight API URL
INGEST_ENDPOINT = f"{BASE_URL}/ingest"
BATCH_INGEST_ENDPOINT = f"{BASE_URL}/ingest/batch"
NUM_EVENTS = 100
INTERVAL = 0.5  # seconds between events

# Sample data
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
STATUS_TYPES = ["outage", "incident", "failure", "normal"]
SOURCES = ["airflow_health_check", "airflow_import_error", "airflow_failed_dag", "dbt", "generic"]

def generate_base_log_event() -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(),
        "source": random.choice(SOURCES),
        "status_type": random.choice(STATUS_TYPES),
        "log_level": random.choice(LOG_LEVELS),
        "message": f"Mock log message for {random.choice(SOURCES)}"
    }

def generate_airflow_health_check_event() -> Dict[str, Any]:
    event = generate_base_log_event()
    event.update({
        "source": "airflow_health_check",
        "metadatabase_status": random.choice(["healthy", "unhealthy"]),
        "scheduler_status": random.choice(["healthy", "unhealthy"]),
        "triggerer_status": random.choice(["healthy", "unhealthy"])
    })
    return event

def generate_airflow_import_error_event() -> Dict[str, Any]:
    event = generate_base_log_event()
    event.update({
        "source": "airflow_import_error",
        "filename": f"/path/to/dag/file_{random.randint(1, 100)}.py",
        "stack_trace": f"ImportError: No module named 'missing_module_{random.randint(1, 10)}'"
    })
    return event

def generate_airflow_failed_dag_event() -> Dict[str, Any]:
    event = generate_base_log_event()
    event.update({
        "source": "airflow_failed_dag",
        "dag_id": f"example_dag_{random.randint(1, 50)}",
        "execution_date": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
        "try_number": random.randint(1, 3)
    })
    return event

def generate_dbt_log_event() -> Dict[str, Any]:
    event = generate_base_log_event()
    event.update({
        "source": "dbt",
        "model_name": f"model_{random.randint(1, 100)}",
        "node_id": f"model.example.model_{random.randint(1, 100)}",
        "run_id": f"run_{random.randint(1000, 9999)}"
    })
    return event

def generate_generic_log_event() -> Dict[str, Any]:
    event = generate_base_log_event()
    event.update({
        "source": "generic",
        "additional_data": {
            "key1": f"value_{random.randint(1, 100)}",
            "key2": random.random(),
            "key3": random.choice([True, False])
        }
    })
    return event

def generate_log_event() -> Dict[str, Any]:
    source = random.choice(SOURCES)
    if source == "airflow_health_check":
        return generate_airflow_health_check_event()
    elif source == "airflow_import_error":
        return generate_airflow_import_error_event()
    elif source == "airflow_failed_dag":
        return generate_airflow_failed_dag_event()
    elif source == "dbt":
        return generate_dbt_log_event()
    else:
        return generate_generic_log_event()

def send_log_event(event: Dict[str, Any]) -> None:
    try:
        response = requests.post(INGEST_ENDPOINT, json={"log_event": event})
        response.raise_for_status()
        print(f"Event sent successfully: {event['source']}")
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