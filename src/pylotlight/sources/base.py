from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel

class BaseSource(ABC):
    @property
    @abstractmethod
    def source_types(self) -> Dict[str, type]:
        pass

    @abstractmethod
    def validate_and_process(self, log_event_dict: Dict[str, Any]) -> BaseModel:
        """
        Validates the given log event dictionary and processes it into a
        pydantic model.

        Args:
            log_event_dict: The log event dictionary to validate and process.

        Returns:
            A pydantic model representing the validated log event.
        """
        pass