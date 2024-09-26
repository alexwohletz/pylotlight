import pytest
from pylotlight.integrations.airflow import get_airflow_status  # Assumes you have this function

def test_get_airflow_status():
    # Mocking an Airflow API response
    with pytest.MonkeyPatch.context() as m:
        m.setattr("pylotlight.integrations.airflow.requests.get", lambda url: MockResponse({"status": "healthy"}))
        
        status = get_airflow_status()
        assert status == "healthy"

class MockResponse:
    def __init__(self, json_data):
        self.json_data = json_data

    def json(self):
        return self.json_data