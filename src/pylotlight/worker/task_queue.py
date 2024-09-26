import json
import time
import logging
from typing import Dict, Type
from redis import Redis
from datetime import datetime
from pylotlight.worker.task import Task
from pylotlight.hooks.base_hook import BaseHook
from pylotlight.hooks.airflow_hook import AirflowHook

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class TaskQueue:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.task_queue_key = 'task_queue'
        self.hook_classes: Dict[str, Type[BaseHook]] = {}
        self.register_hook(AirflowHook)
        # Register other hooks as needed

    def register_hook(self, hook_class: Type[BaseHook]):
        self.hook_classes[hook_class.__name__] = hook_class

    def add_task(self, task: Task):
        task_data = {
            'hook_class': task.hook.__class__.__name__,
            'hook_params': {},  # We don't need to store hook params anymore
            'interval': task.interval,
            'last_run': task.last_run
        }
        self.redis.lpush(self.task_queue_key, json.dumps(task_data, cls=DateTimeEncoder))

    def get_next_task(self) -> Task:
        _, task_data = self.redis.brpop(self.task_queue_key)
        task_dict = json.loads(task_data)
        hook_class = self.hook_classes.get(task_dict['hook_class'])
        if hook_class is None:
            raise ValueError(f"Unknown hook class: {task_dict['hook_class']}")
        hook = hook_class()  # Initialize hook without parameters
        task = Task(hook, task_dict['interval'])
        task.last_run = task_dict.get('last_run', 0)
        return task

    def run_task(self, task: Task):
        current_time = int(time.time())
        if task.should_run(current_time):
            try:
                events = task.run()
                for event in events:
                    self.redis.lpush('log_queue', json.dumps(event.dict(), cls=DateTimeEncoder))
                task.last_run = current_time
            except Exception as e:
                logger.error(f"Error running task for hook {task.hook.__class__.__name__}: {str(e)}")
                error_event = {
                    'timestamp': datetime.now().isoformat(),
                    'source': task.hook.__class__.__name__,
                    'status_type': 'failure',
                    'log_level': 'ERROR',
                    'message': f"Error running task: {str(e)}",
                }
                self.redis.lpush('log_queue', json.dumps(error_event, cls=DateTimeEncoder))
        
        # Re-add the task to the queue
        self.add_task(task)

    def run(self):
        while True:
            try:
                task = self.get_next_task()
                self.run_task(task)
                time.sleep(max(0, task.interval - (int(time.time()) - task.last_run)))
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")
                time.sleep(5)  # Wait 5 seconds before retrying after an error