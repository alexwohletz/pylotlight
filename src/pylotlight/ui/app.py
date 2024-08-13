import streamlit as st
from PIL import Image

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
# Logo
# logo = Image.open("src/pylotlight/ui/components/logo.png")
# st.image(logo, use_column_width=True)

# Title
st.title("Pylot Light Status Page")

# Main status
st.markdown('<div class="main-status"><span class="status-icon green">✓</span>Platform is up and running</div>', unsafe_allow_html=True)

# Sub-statuses in a grid
statuses = {
    "dbt": "No issues",
    "airflow": "No issues",
    "database": "No issues",
    "ci": "No issues"
}

st.markdown('<div class="status-grid">', unsafe_allow_html=True)
for service, status in statuses.items():
    st.markdown(f'<div class="status-item">', unsafe_allow_html=True)
    st.markdown(f'<div class="service-name">{service.upper()}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="service-status"><span class="status-icon green">✓</span>{status}</div>', unsafe_allow_html=True)
    with st.expander("Additional information"):
        st.markdown("No data received yet.")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Status legend
st.markdown("---")
col1, col2, col3, col4, col5 = st.columns(5)
col1.markdown("✓ No Issues")
col2.markdown("🔧 Maintenance")
col3.markdown("🚩 Notice")
col4.markdown("⚠️ Incident")
col5.markdown("🔴 Outage")

# Having trouble section
st.markdown("---")
st.markdown("Having trouble? [Troubleshoot connection issues](https://pylotlight.com/troubleshoot) or email us at support@pylotlight.com")