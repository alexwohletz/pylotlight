import json
import threading
import time
import logging
from redis import Redis
from sqlalchemy.orm import Session
from pylotlight.database.session import SessionLocal, engine
from pylotlight.database.models.log_event import LogEvent as DBLogEvent
from pylotlight.schemas.log_events import LogEvent as SchemaLogEvent, DbtLogEvent, GenericLogEvent, AirflowHealthCheckEvent, AirflowImportErrorEvent, AirflowFailedDagEvent
from pylotlight.worker.task_queue import TaskQueue
from pylotlight.worker.task import Task
from pylotlight.hooks.airflow_hook import AirflowHook
from pylotlight.config import Config
from pydantic import ValidationError
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config()
redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

def process_event(event: dict):
    try:
        # Ensure required fields are present
        required_fields = ['timestamp', 'source', 'status_type', 'log_level', 'message']
        for field in required_fields:
            if field not in event:
                raise ValidationError(f"Missing required field: {field}")

        # Determine the correct LogEvent subclass based on the 'source' field
        source = event['source']
        if source.startswith("airflow_"):
            try:
                if source == "airflow_health_check":
                    log = AirflowHealthCheckEvent(**event)
                elif source == "airflow_import_error":
                    log = AirflowImportErrorEvent(**event)
                elif source == "airflow_failed_dag":
                    log = AirflowFailedDagEvent(**event)
                else:
                    raise ValidationError("Unknown Airflow event type")
            except ValidationError as e:
                logger.error(f"Log event doesn't meet {source} requirements, treating as GenericLogEvent: {str(e)}")
                log = GenericLogEvent(**event)
        elif event['source'] == 'dbt':
            log = DbtLogEvent(**event)
        else:
            log = GenericLogEvent(**event)

        # Store in database
        db = SessionLocal()
        try:
            db_log = DBLogEvent(
                timestamp=log.timestamp,
                source=log.source,
                status_type=log.status_type,
                log_level=log.log_level,
                message=log.message,
                additional_data=log.model_dump_json(exclude={'timestamp', 'source', 'status_type', 'log_level', 'message'})
            )
            db.add(db_log)
            db.commit()
            # Publish to SSE channel
            redis.publish('sse_channel', json.dumps(event))
            logger.info(f"Published event to SSE channel: {json.dumps(event)}")
        finally:
            db.close()
    except ValidationError as e:
        logger.error(f"Validation error processing event: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")

def process_log_queue():
    while True:
        try:
            # Pop item from Redis list
            _, log_json = redis.brpop('log_queue')
            log_data = json.loads(log_json)
            process_event(log_data)
        except Exception as e:
            logger.error(f"Error in process_log_queue: {str(e)}")
            time.sleep(5)  # Wait for 5 seconds before trying again

def run_task_queue():
    task_queue = TaskQueue(redis)

    # Add tasks to the queue based on configuration
    for hook_name, hook_config in config.HOOKS.items():
        if hook_config['enabled']:
            if hook_name == 'airflow':
                hook = AirflowHook()
                task = Task(hook, interval=hook_config['polling_interval'])
                task_queue.add_task(task)
            # Add other hooks here as they are implemented

    # Run the task queue
    while True:
        try:
            task_queue.run()
        except Exception as e:
            logger.error(f"Error in run_task_queue: {str(e)}")
            time.sleep(5)  # Wait for 5 seconds before trying again

def run_worker():
    # Start the log queue processing thread
    log_thread = threading.Thread(target=process_log_queue)
    log_thread.start()

    # Run the task queue in the main thread
    run_task_queue()

if __name__ == "__main__":
    run_worker()