import streamlit as st
import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
import re
from collections import deque
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = "http://fastapi:8000"  # Adjust as needed

class Severity(Enum):
    NO_ISSUES = 0
    NOTICE = 1
    INCIDENT = 2
    OUTAGE = 3

class EventTimeline:
    def __init__(self, max_events: int = 10):
        self.events: deque = deque(maxlen=max_events)

    def add_event(self, event: Dict[str, Any]) -> None:
        self.events.append(event)

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self.events)

class ErrorState:
    def __init__(self, duration: timedelta = timedelta(minutes=30)):
        self.error: Optional[Dict[str, Any]] = None
        self.error_time: Optional[datetime] = None
        self.duration: timedelta = duration

    def set_error(self, error: Dict[str, Any]) -> None:
        self.error = error
        self.error_time = datetime.now()

    def clear_error(self) -> None:
        self.error = None
        self.error_time = None

    def is_error_active(self) -> bool:
        if self.error and self.error_time:
            return datetime.now() - self.error_time < self.duration
        return False

    def get_error(self) -> Optional[Dict[str, Any]]:
        return self.error if self.is_error_active() else None

# Helper Functions
def get_status_icon_and_color(status_type: str) -> Tuple[str, str]:
    status_type = status_type.lower().strip()
    if status_type in ["normal", "healthy", "no issues"]:
        return "✓", "green"
    elif status_type == "notice":
        return "🚩", "yellow"
    elif status_type in ["incident", "unhealthy"]:
        return "⚠️", "orange"
    elif status_type in ["outage", "failure"]:
        return "🔴", "red"
    else:
        return "🔧", "blue"  # For maintenance or unknown status

async def fetch_sse_events() -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/sse", headers={'Accept': 'text/event-stream'}) as response:
            buffer = ""
            async for line in response.content:
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    buffer += decoded_line + "\n"
                    
                    if buffer.endswith("\n\n"):
                        event = parse_sse_event(buffer.strip())
                        if event:
                            yield event
                        buffer = ""

def parse_sse_event(event_data: str) -> Optional[Dict[str, Any]]:
    lines = event_data.split("\n")
    event_type = None
    data = []
    
    for line in lines:
        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data.append(line.split(":", 1)[1].strip())
    
    if event_type == "ping":
        logger.debug("Received ping event")
        return None
    elif event_type == "update" and data:
        full_data = " ".join(data).strip()
        if full_data:
            # Remove potential timestamp prefix
            full_data = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ ', '', full_data)
            try:
                return json.loads(full_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON: {e}. Raw data: {full_data}")
    elif data and all(d == ": keep-alive" or d == "" for d in data):
        logger.debug("Received keep-alive message")
    else:
        logger.warning(f"Received unexpected SSE data: {event_data}")
    
    return None

def get_severity(status_type: str) -> int:
    status_type = status_type.lower().strip()
    if status_type in ["normal", "healthy", "no issues"]:
        return Severity.NO_ISSUES.value
    elif status_type == "notice":
        return Severity.NOTICE.value
    elif status_type in ["incident", "unhealthy"]:
        return Severity.INCIDENT.value
    elif status_type in ["outage", "failure"]:
        return Severity.OUTAGE.value
    else:
        return Severity.NO_ISSUES.value

def process_update(update: Dict[str, Any]) -> bool:
    if 'source' in update and 'status_type' in update:
        source = update['source']
        status_type = update['status_type']
        
        # Map the source to the correct key in st.session_state.statuses
        service = next((s for s in ['airflow', 'dbt', 'database', 'ci'] if s in source), source)
        component = source.replace(f"{service}_", "")
        
        if service in st.session_state.statuses:
            severity = get_severity(status_type)
            current_severity = get_severity(st.session_state.statuses[service].get('overall', 'No issues'))
            
            if component:
                st.session_state.statuses[service][component] = status_type.capitalize()
            else:
                st.session_state.statuses[service]['overall'] = status_type.capitalize()
            
            st.session_state.last_log_messages[service] = update.get('message', '')
            st.session_state.timelines[service].add_event(update)
            
            if severity > current_severity:
                st.session_state.error_states[service].set_error(update)
            elif severity == Severity.NO_ISSUES.value:
                st.session_state.error_states[service].clear_error()
            
            # Update overall status
            overall_severity = max(get_severity(status) for status in st.session_state.statuses[service].values())
            st.session_state.statuses[service]['overall'] = Severity(overall_severity).name.lower().replace("_", " ").capitalize()
            
            logger.info(f"Updated status for {service} - {component if component else 'overall'}: {status_type}")
            return True
        else:
            logger.warning(f"Unknown source in status update: {source}")
    return False

def update_ui() -> None:
    # Main status
    main_status = max((st.session_state.statuses[service].get('overall', 'No issues') for service in st.session_state.statuses),
                      key=lambda x: get_severity(x))
    main_icon, main_color = get_status_icon_and_color(main_status)
    st.markdown(f'<div class="main-status"><span class="status-icon {main_color}">{main_icon}</span>Platform Status: {main_status}</div>', unsafe_allow_html=True)

    # Sub-statuses in a grid
    st.markdown('<div class="status-grid">', unsafe_allow_html=True)
    for service, status in st.session_state.statuses.items():
        st.markdown(f'<div class="status-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="service-name">{service.upper()}</div>', unsafe_allow_html=True)
        overall_status = status.get('overall', 'No issues')
        icon, color = get_status_icon_and_color(overall_status)
        st.markdown(f'<div class="service-status"><span class="status-icon {color}">{icon}</span>{overall_status}</div>', unsafe_allow_html=True)
        with st.expander("Additional information"):
            for component, component_status in status.items():
                if component != 'overall':
                    st.markdown(f"**{component.capitalize()}**: {component_status}")
            st.markdown("---")
            st.markdown("**Recent Events:**")
            for event in st.session_state.timelines[service].get_events():
                st.markdown(f"- {event.get('timestamp', 'N/A')}: {event.get('message', 'No message')}")
            st.markdown("---")
            last_message = st.session_state.last_log_messages.get(service, "No additional information available.")
            st.markdown(f"**Last Message:** {last_message}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Status legend
    st.markdown("---")
    cols = st.columns(5)
    cols[0].markdown("✓ No Issues")
    cols[1].markdown("🔧 Maintenance")
    cols[2].markdown("🚩 Notice")
    cols[3].markdown("⚠️ Incident")
    cols[4].markdown("🔴 Outage/Failure")

    # Having trouble section
    st.markdown("---")
    st.markdown("Having trouble? [Troubleshoot connection issues](https://pylotlight.com/troubleshoot) or email us at support@pylotlight.com")

    # Debug info
    st.empty().text(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main() -> None:
    # Set page config
    st.set_page_config(page_title="Pylot Light Status", layout="wide")

    # Custom CSS for styling
    st.markdown("""
    <style>
        .main-status {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
            text-align: center;
        }
        .status-grid {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 30px;
        }
        .status-item {
            width: 200px;
            text-align: center;
        }
        .status-icon {
            font-size: 24px;
            margin-right: 10px;
        }
        .green { color: #36a64f; }
        .red { color: #ff4136; }
        .yellow { color: #ffd700; }
        .orange { color: #ffa500; }
        .stExpander {
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .service-name {
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 5px;
        }
        .service-status {
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'statuses' not in st.session_state:
        st.session_state.statuses = {
            "airflow": {
                "overall": "No issues",
                "health_check": "No issues",
                "import_status": "No issues",
                "dag_execution": "No issues"
            },
            "dbt": {
                "overall": "No issues",
                "execution": "No issues",
                "compilation": "No issues"
            },
            "database": {
                "overall": "No issues",
                "connection": "No issues",
                "performance": "No issues"
            },
            "ci": {
                "overall": "No issues",
                "builds": "No issues",
                "tests": "No issues"
            }
        }
    if 'last_log_messages' not in st.session_state:
        st.session_state.last_log_messages = {service: "" for service in st.session_state.statuses}
    if 'timelines' not in st.session_state:
        st.session_state.timelines= {service: EventTimeline() for service in st.session_state.statuses}
    if 'error_states' not in st.session_state:
        st.session_state.error_states = {service: ErrorState() for service in st.session_state.statuses}

    # Main Streamlit UI
    st.title("Pylot Light Status Page")

    # Create a placeholder for the main content
    main_content = st.empty()

    # Main loop for updating the UI
    while True:
        with main_content.container():
            update_ui()
        
        try:
            async for event in fetch_sse_events():
                if event and process_update(event):
                    st.rerun()
        except aiohttp.ClientError as e:
            logger.error(f"Connection error: {e}")
            await asyncio.sleep(5)  # Wait before retrying
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    asyncio.run(main())