from datetime import datetime
from typing import Dict, Any

class AirflowIntegration:
    @staticmethod
    def process_airflow_log(log_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an Airflow log event and return a standardized format.
        """
        return {
            "source": "airflow",
            "timestamp": datetime.fromisoformat(log_event["execution_date"]),
            "level": log_event["level"],
            "message": log_event["message"],
            "dag_id": log_event["dag_id"],
            "task_id": log_event["task_id"],
            "execution_date": datetime.fromisoformat(log_event["execution_date"]),
            "status": "failed" if log_event["level"] == "error" else "success"
        }

    @staticmethod
    def get_task_status(log_events: list[Dict[str, Any]]) -> Dict[str, str]:
        """
        Determine the status of tasks based on log events.
        """
        task_status = {}
        for event in log_events:
            task_key = f"{event['dag_id']}/{event['task_id']}"
            if event["level"] == "error":
                task_status[task_key] = "failed"
            elif task_key not in task_status:
                task_status[task_key] = "success"
        return task_status