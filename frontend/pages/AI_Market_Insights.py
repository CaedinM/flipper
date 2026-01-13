import streamlit as st
import sys
from pathlib import Path

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.state import init_state

if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="AI Market Insights", layout="wide")
st.title("AI Market Insights")
st.caption("Let AI agents find upcoming profitable drops for you")

st.caption("Note: Only works for sneakers currently, updates coming soon!")

col1, col2, col3 = st.columns([2,1,1])
with col1:
    category = st.selectbox(
        "Category",
        ["Sneakers"],
        index=0
    )
with col2:
    max_items = st.number_input(label="Max Results", min_value=1, max_value=10, step=1)
with col3:
    run_scan = st.button("🔎 Run AI Scan", type="primary", use_container_width=True)

if "suggestions" not in st.session_state:
    st.session_state.suggestions = []

if run_scan:
    with st.spinner("Running CrewAI agents…"):
        st.session_state.suggestions = run_market_research(category=category, max_items=int(max_items))
    st.success("New suggestions loaded below.")

st.divider()

