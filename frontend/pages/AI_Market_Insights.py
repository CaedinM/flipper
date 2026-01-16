import streamlit as st
import sys
from pathlib import Path

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.state import init_state
from backend.crews.sneaker_market_reseach.main import run_market_research
from backend.db import run_query_df

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

# Previous Scans Section
st.divider()
st.subheader("Previous Scans")

def get_releases_df(refresh_token: int):
    return run_query_df("""
        SELECT
            r.product_name AS "Product Name",
            r.brand AS "Brand",
            r.release_date AS "Release Date",
            r.retail_price AS "Retail Price",
            r.resale_estimate AS "Resale Estimate",
            r.confidence_score AS "Confidence",
            ar.start_time AS "Scan Date"
        FROM releases r
        JOIN agent_runs ar ON r.run_id = ar.id
        WHERE ar.status = 'succeeded'
        ORDER BY ar.start_time DESC, r.product_name
    """, refresh_token)

releases_history = get_releases_df(st.session_state.refresh_token)

if not releases_history.empty:
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Releases Tracked", len(releases_history))
    with col2:
        avg_confidence = releases_history["Confidence"].mean()
        st.metric("Avg Confidence Score", f"{avg_confidence:.0f}%")
    with col3:
        last_scan = releases_history["Scan Date"].max()
        st.metric("Last Scan", last_scan.strftime("%m/%d/%Y %H:%M"))

    st.dataframe(
        releases_history,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Product Name": st.column_config.TextColumn("Product Name", width="large"),
            "Brand": st.column_config.TextColumn("Brand"),
            "Release Date": st.column_config.DateColumn("Release Date", format="MM/DD/YY"),
            "Retail Price": st.column_config.NumberColumn("Retail", format="$%d"),
            "Resale Estimate": st.column_config.NumberColumn("Resale Est.", format="$%d"),
            "Confidence": st.column_config.NumberColumn("Confidence", format="%d%%"),
            "Scan Date": st.column_config.DatetimeColumn("Scan Date", format="MM/DD/YY HH:mm"),
        }
    )
else:
    st.info("No previous scans found. Run an AI scan to see historical data.")
