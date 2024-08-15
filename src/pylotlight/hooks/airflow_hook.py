import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Union
import base64
import logging
from pylotlight.hooks.base_hook import BaseHook
from pylotlight.config import Config
from pylotlight.schemas.log_events import AirflowHealthCheckEvent, AirflowImportErrorEvent, AirflowFailedDagEvent
import json 
import time
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class AirflowHook(BaseHook):
    def __init__(self):
        config = Config.get_hook_config('airflow')
        self.base_url = config['base_url']
        self.auth = base64.b64encode(f"{config['api_user']}:{config['api_password']}".encode()).decode()
        self.request_delay = 1  # Delay between requests in seconds
        self.max_retries = 3  # Maximum number of retries for a request

    def _make_request(self, endpoint: str, method: str = 'GET', params: Dict[str, Any] = None, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Type': 'application/json'
        }
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, headers=headers, params=params, json=payload, timeout=10)
                response.raise_for_status()
                time.sleep(self.request_delay)  # Delay between requests
                return response.json()
            except RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * self.request_delay
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached. Error making request to Airflow API: {str(e)}")
                    return {'error': str(e)}

    def check_connection(self) -> bool:
        try:
            health_check = self.get_health_check()
            if 'error' in health_check:
                logger.error(f"Connection to Airflow failed: {health_check['error']}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking connection to Airflow: {str(e)}")
            return False

    def get_health_check(self) -> Dict[str, Any]:
        return self._make_request('/health')

    def get_import_errors(self) -> List[Dict[str, Any]]:
        return self._make_request('/importErrors')

    def get_failed_dags(self) -> List[Dict[str, Any]]:
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=24)
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        payload = {
            "states": ["failed"],
            "start_date_gte": start_date_str,
        }

        response = self._make_request('/dags/~/dagRuns/list', 'POST', payload=payload)
        dag_runs = response.get('dag_runs', [])
        logger.info(f"Found {len(dag_runs)} failed DAG runs in the last 24 hours.")
        return dag_runs

    def push_events(self) -> List[Union[AirflowHealthCheckEvent, AirflowImportErrorEvent, AirflowFailedDagEvent]]:
        if not self.check_connection():
            logger.error("Failed to establish connection with Airflow. Aborting push_events().")
            return []

        events = []

        # Health check event
        health_check = self.get_health_check()
        metadata_health_check = health_check.get('metadatabase', {}).get('status', '')
        scheduler_health_check = health_check.get('scheduler', {}).get('status', '')
        triggerer_health_check = health_check.get('triggerer', {}).get('status', '')
        
        health_status = 'normal' if all(status == 'healthy' for status in [metadata_health_check, scheduler_health_check, triggerer_health_check]) else 'incident'
        log_level = 'INFO' if health_status == 'normal' else 'ERROR'
        
        events.append(AirflowHealthCheckEvent(
            timestamp=datetime.now(timezone.utc),
            source='airflow_health_check',
            status_type=health_status,
            log_level=log_level,
            message=f"Health check: Metadatabase: {metadata_health_check}, Scheduler: {scheduler_health_check}, Triggerer: {triggerer_health_check}",
            metadatabase_status=metadata_health_check,
            scheduler_status=scheduler_health_check,
            triggerer_status=triggerer_health_check
        ))

        # Import errors event
        import_errors = self.get_import_errors()
        list_of_import_errors = import_errors.get('import_errors', [])
        if list_of_import_errors:
            for error in list_of_import_errors:
                events.append(AirflowImportErrorEvent(
                    timestamp=datetime.fromisoformat(error['timestamp']),
                    source='airflow_import_error',
                    status_type='failure',
                    log_level='ERROR',
                    message=f"Import error: {error['filename']} - {error['stack_trace']}",
                    filename=error['filename'],
                    stack_trace=error['stack_trace']
                ))
        else:
            events.append(AirflowImportErrorEvent(
                timestamp=datetime.now(timezone.utc),
                source='airflow_import_error',
                status_type='normal',
                log_level='INFO',
                message="No import errors found.",
                filename='N/A',
                stack_trace='N/A'
            ))

        # Failed DAGs event
        failed_dagruns = self.get_failed_dags()
        for dag_run in failed_dagruns:
            events.append(AirflowFailedDagEvent(
                timestamp=datetime.fromisoformat(dag_run['execution_date']),
                source='airflow_failed_dag',
                status_type='failure',
                log_level='ERROR',
                message=f"DAG failed: {dag_run['dag_id']}",
                dag_id=dag_run['dag_id'],
                execution_date=datetime.fromisoformat(dag_run['execution_date']),
                try_number=1
            ))

        return events

if __name__ == '__main__':
    hook = AirflowHook()
    print(hook.push_events())