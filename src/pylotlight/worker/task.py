from typing import List, Dict, Any
from pylotlight.hooks.base_hook import BaseHook

class Task:
    def __init__(self, hook: BaseHook, interval: int):
        self.hook = hook
        self.interval = interval
        self.last_run = 0

    def should_run(self, current_time: int) -> bool:
        return current_time - self.last_run >= self.interval

    def run(self) -> List[Dict[str, Any]]:
        return self.hook.push_events()