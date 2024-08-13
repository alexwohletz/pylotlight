import streamlit as st
import requests
import time

def main():
    st.title("Pylot Light Dashboard")

    if st.button("Fetch Latest Events"):
        events = fetch_events()
        display_events(events)

def fetch_events():
    response = requests.get("http://localhost:8000/events")
    return response.json()

def display_events(events):
    for event in events:
        st.write(f"Source: {event['source']}")
        st.write(f"Timestamp: {event['timestamp']}")
        st.write(f"Data: {event['data']}")
        st.write("---")

if __name__ == "__main__":
    main()