import pytest
from pylotlight.data.api import ingest_data  # Assumes you have this function

def test_ingest_data():
    # Assuming ingest_data returns a dictionary of ingested data
    result = ingest_data()
    assert isinstance(result, dict)
    assert "airflow" in result
    assert "dbt" in result
