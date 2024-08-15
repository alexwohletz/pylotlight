import streamlit as st
from sseclient import SSEClient
import json

# Assume API_BASE_URL is set to your FastAPI backend URL
API_BASE_URL = "http://localhost:8000"  # Adjust as needed

def main():
    st.title("Pylot Light Log Dashboard")

    # Initialize session state for log events if it doesn't exist
    if 'log_events' not in st.session_state:
        st.session_state.log_events = []

    # Display current log events
    for log in st.session_state.log_events:
        st.write(f"[{log['timestamp']}] {log['source']} - {log['log_level']}: {log['message']}")

    # SSE Client setup
    if 'sse_client' not in st.session_state:
        st.session_state.sse_client = SSEClient(f"{API_BASE_URL}/sse")

    # Placeholder for updates
    update_placeholder = st.empty()

    # Listen for SSE events
    for event in st.session_state.sse_client:
        if event.event == "update":
            log_data = json.loads(event.data)
            update_placeholder.write(f"New log received: {log_data['message']}")
            
            # Add the new log event to our list
            st.session_state.log_events.append(log_data)
            
            # Keep only the last 100 log events to prevent the list from growing too large
            st.session_state.log_events = st.session_state.log_events[-100:]
            
            # Rerun the app to refresh the displayed log events
            st.experimental_rerun()

if __name__ == "__main__":
    main()