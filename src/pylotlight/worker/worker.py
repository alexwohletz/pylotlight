import json
import threading
import time
import logging
from redis import Redis
from sqlalchemy.orm import Session
from pylotlight.database.session import SessionLocal, engine
from pylotlight.database.models.log_event import LogEvent as DBLogEvent
from pylotlight.schemas.log_events import LogEvent as SchemaLogEvent, GenericLogEvent
from pylotlight.worker.task_queue import TaskQueue
from pylotlight.worker.task import Task
from pylotlight.hooks.airflow_hook import AirflowHook
from pylotlight.config import Config
from pydantic import ValidationError
from pylotlight.sources import get_source_handler, BaseSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config()
redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)

def process_event(event: dict):
    try:
        # Ensure required fields are present
        required_fields = ['timestamp', 'source', 'source_type', 'status_type', 'log_level', 'message']
        for field in required_fields:
            if field not in event:
                raise ValidationError(f"Missing required field: {field}")

        # Get the appropriate log source handler
        source = event['source']
        try:
            source_handler = get_source_handler(source)
        except ValueError:
            logger.warning(f"No specific LogSource handler found for source: {source}. Using GenericLogEvent.")
            source_handler = None

        if source_handler:
            try:
                parsed_log = source_handler.validate_and_process(event)
            except Exception as e:
                logger.error(f"Error processing log with {source} source: {str(e)}")
                parsed_log = GenericLogEvent(**event)
        else:
            parsed_log = GenericLogEvent(**event)

        # Store in database
        db = SessionLocal()
        try:
            db_log = DBLogEvent(
                timestamp=parsed_log.timestamp,
                source=parsed_log.source,
                source_type=parsed_log.source_type,
                status_type=parsed_log.status_type,
                log_level=parsed_log.log_level,
                message=parsed_log.message,
                additional_data=parsed_log.model_dump_json(exclude={'timestamp', 'source', 'source_type', 'status_type', 'log_level', 'message'})
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