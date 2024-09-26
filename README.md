# Pylot Light

Pylot Light is a lightweight log analysis tool designed to process and analyze log events from various sources, with a focus on Airflow and dbt logs.

## Project Structure

The project is organized as follows:

- `src/pylotlight/schemas/log_events.py`: Defines the schema for different types of log events using Pydantic models.
- `src/pylotlight/hooks/`: Contains hook implementations for different log sources.
- `src/pylotlight/sources/`: Implements log source parsers and processors.

## Adding New Log Sources

To add a new log source to Pylot Light, follow these steps:

1. Define the log event schema:
   - Open `src/pylotlight/schemas/log_events.py`
   - Create a new Pydantic model that inherits from `LogEventBase` or another appropriate base class
   - Define the fields specific to your new log source

2. Create a new source file:
   - Add a new Python file in the `src/pylotlight/sources/` directory (e.g., `new_source.py`)
   - Implement a class that inherits from the base source class in `base.py`
   - Implement methods for parsing and processing log events from your new source

3. (Optional) Create a new hook:
   - If your log source requires specific connection logic, add a new Python file in the `src/pylotlight/hooks/` directory (e.g., `new_source_hook.py`)
   - Implement a class that inherits from `BaseHook` in `base_hook.py`
   - Implement methods for connecting to and retrieving logs from your new source

4. Update the main application:
   - Modify the main application code to recognize and use your new log source
   - Update any relevant configuration files or environment variables

Example of adding a new log event schema:

```python
# In src/pylotlight/schemas/log_events.py

class NewSourceLogEvent(LogEventBase):
    source: Literal["new_source"] = Field(default="new_source")
    source_type: Literal["new_source_type"] = Field(default="new_source_type")
    custom_field: str = Field(..., description="A custom field for the new source")

# Update the LogEvent union
LogEvent = Union[AirflowHealthCheckEvent, ..., NewSourceLogEvent]
```

Example of adding a new source:

```python
# In src/pylotlight/sources/new_source.py

from .base import BaseSource
from ..schemas.log_events import NewSourceLogEvent

class NewSource(BaseSource):
    def parse_log(self, log_data: str) -> NewSourceLogEvent:
        # Implement parsing logic here
        pass

    def process_log(self, log_event: NewSourceLogEvent):
        # Implement processing logic here
        pass
```

## Running the Project Locally

To run Pylot Light on your local machine, follow these steps:

1. Ensure you have Python 3.7 or higher installed on your system.

2. Clone the repository:
   ```
   git clone https://github.com/yourusername/pylotlight.git
   cd pylotlight
   ```

3. (Optional) Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Set up any necessary environment variables or configuration files for your log sources.

6. Run the main application:
   ```
   docker-compose up -d
   ```

7. Use the provided API endpoints to ingest, retrieve, and analyze log events.

For more detailed usage instructions and available options, refer to the application's documentation or help command.

## API Endpoints

Pylot Light provides several API endpoints for log ingestion and retrieval:

- `POST /ingest`: Ingest a single log event
- `POST /ingest/batch`: Ingest multiple log events in a batch
- `GET /logs`: Retrieve logs based on specified criteria

Refer to the `LogIngestionRequest`, `BatchLogIngestionRequest`, and `LogRetrievalRequest` models in `src/pylotlight/schemas/log_events.py` for the expected request formats.

## Server-Sent Events (SSE)

Pylot Light supports Server-Sent Events for real-time log streaming. The `SSEMessage` model in `src/pylotlight/schemas/log_events.py` defines the structure of SSE messages.

For more information on using the API and SSE functionality, please refer to the API documentation.
