from typing import Dict, Any, Type
from pydantic import ValidationError
from .base import BaseSource
from pylotlight.schemas.log_events import (
    LogEventBase,
    DbtLogEvent,
    GenericLogEvent
)
class DbtSource(BaseSource):
    @property
    def source_types(self) -> Dict[str, Type[LogEventBase]]:
        return {
            "dbt": DbtLogEvent,
        }

    def validate_and_process(self, log_event_dict: Dict[str, Any]) -> LogEventBase:
        source_type = log_event_dict.get("source_type")
        if source_type not in self.source_types:
            raise ValueError(f"Unknown dbt source type: {source_type}")
        
        event_class = self.source_types[source_type]
        try:
            return event_class(**log_event_dict)
        except ValidationError as e:
            # Log the validation error
            print(f"Validation error for {source_type}: {str(e)}")
            # Fall back to GenericLogEvent
            return GenericLogEvent(**log_event_dict)