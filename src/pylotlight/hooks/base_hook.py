from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseHook(ABC):
    @abstractmethod
    def push_events(self) -> List[Dict[str, Any]]:
        pass