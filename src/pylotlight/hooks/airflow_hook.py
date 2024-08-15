import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import base64
import logging
from pylotlight.hooks.base_hook import BaseHook
from pylotlight.config import Config
import json 
logger = logging.getLogger(__name__)

class AirflowHook(BaseHook):
    def __init__(self):
        config = Config.get_hook_config('airflow')
        self.base_url = config['base_url']
        self.auth = base64.b64encode(f"{config['api_user']}:{config['api_password']}".encode()).decode()

    def _make_request(self, endpoint: str, method: str = 'GET', params: Dict[str, Any] = None, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Type': 'application/json'
        }
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=headers, params=params, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Airflow API: {str(e)}")
            return {'error': str(e)}

    def get_health_check(self) -> Dict[str, Any]:
        return self._make_request('/health')

    def get_import_errors(self) -> List[Dict[str, Any]]:
        return self._make_request('/importErrors')

    def get_failed_dags(self) -> List[Dict[str, Any]]:
        # Calculate the timestamp for 24 hours ago
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=24)

        # Format dates in ISO 8601 format
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Prepare the request payload
        payload = {
            "states": ["failed"],
            "start_date_gte": start_date_str,
            # "page_limit": 100  # Adjust this value based on your needs
        }

        response = self._make_request('/dags/~/dagRuns/list', 'POST', payload=payload)
        # Check if the request was successful
        dag_runs = response['dag_runs']
        logger.info(f"Found {len(dag_runs)} failed DAG runs in the last 24 hours:")
        return dag_runs
        

    def push_events(self) -> List[Dict[str, Any]]:
        events = []

        # Health check event
        health_check = self.get_health_check()
        metadata_health_check = health_check.get('metadatabase', {}).get('status', '')
        scheduler_health_check = health_check.get('scheduler', {}).get('status', '')
        triggerer_health_check = health_check.get('triggerer', {}).get('status', '')
        if metadata_health_check == 'healthy' and scheduler_health_check == 'healthy' and triggerer_health_check == 'healthy':
            events.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'airflow',
                'status_type': 'normal',
                'log_level': 'INFO',
                'message': f"Health check passed! Metadatabase: {metadata_health_check}, Scheduler: {scheduler_health_check}, Triggerer: {triggerer_health_check}",
                'dag_id': 'N/A',
                'task_id': 'N/A',
                'execution_date': datetime.now(timezone.utc).isoformat(),
                'try_number': 0
            })
        else:
            events.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'airflow',
                'status_type': 'incident',
                'log_level': 'ERROR',
                'message': f"Warning: Health check failed! Metadatabase: {metadata_health_check}, Scheduler: {scheduler_health_check}, Triggerer: {triggerer_health_check}",
                'dag_id': 'N/A',
                'task_id': 'N/A',
                'execution_date': datetime.now(timezone.utc).isoformat(),
                'try_number': 0
            })
        # Import errors event
        import_errors = self.get_import_errors()
        list_of_import_errors = import_errors.get('import_errors', [])
        if list_of_import_errors:
            for error in list_of_import_errors:
                events.append({
                    'timestamp': error['timestamp'],
                    'source': 'airflow',
                    'status_type': 'failure',
                    'log_level': 'ERROR',
                    'message': f"Import error: {error['filename']} - {error['stack_trace']}",
                    'dag_id': 'N/A',
                    'task_id': 'N/A',
                    'execution_date': error['timestamp'],
                    'try_number': 0
                })
        else:
            events.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'airflow',
                'status_type': 'normal',
                'log_level': 'INFO',
                'message': f"No import errors found.",
                'dag_id': 'N/A',
                'task_id': 'N/A',
                'execution_date': datetime.now(timezone.utc).isoformat(),
                'try_number': 0
            })

        # Failed DAGs event
        failed_dagruns = self.get_failed_dags()
        for dag_run in failed_dagruns:
            events.append({
                'timestamp': dag_run['execution_date'],
                'source': 'airflow',
                'status_type': 'failure',
                'log_level': 'ERROR',
                'message': f"DAG failed: {dag_run['dag_id']}",
                'dag_id': dag_run['dag_id'],
                'task_id': 'N/A',
                'execution_date': dag_run['execution_date'],
                'try_number': 0
            })

        return events
    
if __name__ == '__main__':
    hook = AirflowHook()
    print(hook.push_events())