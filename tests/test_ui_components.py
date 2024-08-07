import pytest
import streamlit as st
from pylotlight.ui.components.metrics_card import metrics_card  # Assumes you have this component

def test_metrics_card():
    # Mocking Streamlit's st.metric function
    with pytest.MonkeyPatch.context() as m:
        mocked_metric = m.setattr(st, "metric", lambda label, value, delta=None: None)
        
        # Call your component
        metrics_card("Test Metric", 100, 10)
        
        # Assert that st.metric was called
        assert mocked_metric.call_count == 1
