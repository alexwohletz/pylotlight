import streamlit as st
import asyncio
import aiohttp
import json
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = "http://fastapi:8000"  # Adjust as needed

# Helper Functions
def get_status_icon_and_color(status_type):
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

async def fetch_sse_events():
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

def parse_sse_event(event_data):
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

def process_update(update):
    if 'source' in update and 'status_type' in update:
        source = update['source']
        status_type = update['status_type']
        
        # Map the source to the correct key in st.session_state.statuses
        source = next((s for s in ['airflow', 'dbt', 'database', 'ci'] if s in source), source)
        
        if source in st.session_state.statuses:
            st.session_state.statuses[source] = status_type.capitalize()
            st.session_state.last_log_messages[source] = update.get('message', '')
            logger.info(f"Updated status for {source}: {status_type}")
            return True
        else:
            logger.warning(f"Unknown source in status update: {source}")
    return False

def update_ui():
    # Main status
    main_status = max(st.session_state.statuses.values(), key=lambda x: ["No issues", "Notice", "Incident", "Outage", "Failure"].index(x) if x in ["No issues", "Notice", "Incident", "Outage", "Failure"] else -1)
    main_icon, main_color = get_status_icon_and_color(main_status)
    st.markdown(f'<div class="main-status"><span class="status-icon {main_color}">{main_icon}</span>Platform Status</div>', unsafe_allow_html=True)

    # Sub-statuses in a grid
    st.markdown('<div class="status-grid">', unsafe_allow_html=True)
    for service, status in st.session_state.statuses.items():
        st.markdown(f'<div class="status-item">', unsafe_allow_html=True)
        st.markdown(f'<div class="service-name">{service.upper()}</div>', unsafe_allow_html=True)
        icon, color = get_status_icon_and_color(status.lower())
        st.markdown(f'<div class="service-status"><span class="status-icon {color}">{icon}</span>{status}</div>', unsafe_allow_html=True)
        with st.expander("Additional information"):
            last_message = st.session_state.last_log_messages.get(service, "No additional information available.")
            st.markdown(last_message)
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

async def main():
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
            "dbt": "No issues",
            "airflow": "No issues",
            "database": "No issues",
            "ci": "No issues"
        }
    if 'last_log_messages' not in st.session_state:
        st.session_state.last_log_messages = {
            "dbt": "",
            "airflow": "",
            "database": "",
            "ci": ""
        }

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