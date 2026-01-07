import streamlit as st
import pandas as pd
import json
import datetime as dt
import sys
from pathlib import Path

# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..state import init_state
from backend.db import run_query_df # adjust to your helper names
from backend.crews.sneaker_market_reseach.agents.market_research import run_market_research  # your CrewAI runner

if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="AI Market Insights", layout="wide")
st.title("🤖 AI Market Insights")
st.caption("Let AI agents find upcoming profitable drop for you")

col1, col2, col3 = st.columns([2,1,1])
with col1:
    category = st.selectbox(
        "Category",
        ["Pokemon Cards", "Sports Cards", "Streetwear", "Toys", "Vinyl"],
        index=0
    )
with col2:
    max_items = st.number_input(label="Suggestions", min_value=1, max_value=6, step=1)
with col3:
    run_scan = st.button("🔎 Run AI Scan", type="primary", use_container_width=True)

if "suggestions" not in st.session_state:
    st.session_state.suggestions = []

if run_scan:
    with st.spinner("Running CrewAI agents…"):
        st.session_state.suggestions = run_market_research(category=category, max_items=int(max_items))
    st.success("New suggestions loaded below.")

st.divider()

