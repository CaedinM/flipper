import streamlit as st
import sys
from pathlib import Path

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.state import init_state
from backend.crews.sneaker_market_reseach.main import run_market_research

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
    max_items = st.number_input(label="Max Results", min_value=1, max_value=10, value=3, step=1)
with col3:
    run_scan = st.button("Run AI Scan", type="primary", width="stretch")

if "releases_df" not in st.session_state:
    st.session_state.releases_df = None

if run_scan:
    with st.spinner("Running CrewAI agents... This may take a few minutes."):
        try:
            st.session_state.releases_df = run_market_research(num_items=int(max_items))
            st.success(f"Found {len(st.session_state.releases_df)} releases! Data saved to database.")
        except Exception as e:
            st.error(f"Error running AI scan: {e}")

st.divider()

# Display results
if st.session_state.releases_df is not None and not st.session_state.releases_df.empty:
    st.subheader("Upcoming Releases")
    st.dataframe(
        st.session_state.releases_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Product Name": st.column_config.TextColumn("Product Name", width="large"),
            "Brand": st.column_config.TextColumn("Brand"),
            "Release Date": st.column_config.DateColumn("Release Date", format="MM/DD/YY"),
            "Retail Price": st.column_config.TextColumn("Retail"),
            "Resale Estimate": st.column_config.TextColumn("Resale Est."),
            "Confidence": st.column_config.TextColumn("Confidence"),
            "Retailers": st.column_config.TextColumn("Retailers", width="medium"),
            "Sources": st.column_config.TextColumn("Sources", width="large"),
        }
    )
elif st.session_state.releases_df is not None:
    st.info("No releases found. Try running another scan.")
else:
    st.info("Click 'Run AI Scan' to find upcoming releases.")
