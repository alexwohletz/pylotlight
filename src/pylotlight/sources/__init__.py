from .base import BaseSource
from .airflow import AirflowSource
from .dbt import DbtSource

source_registry = {
    "airflow": AirflowSource(),
    "dbt": DbtSource(),
}

def get_source_handler(source: str) -> BaseSource:
    handler = source_registry.get(source)
    if not handler:
        raise ValueError(f"Unknown source: {source}")
    return handler