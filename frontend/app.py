import streamlit as st
import pandas as pd
import altair as alt
import datetime as dt

from psycopg2.extras import execute_values
from pathlib import Path

import sys
from pathlib import Path
# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import *
from components.charts import *
from components.new_order_form import render_new_order_form
from state import init_state

if "refresh_token" not in st.session_state:
    init_state()

# Page config
st.set_page_config(
    page_title="Flipper - Resell Analytics Platform",
    page_icon="🦭",  # you can swap this for your logo favicon later
    layout="wide"
)

def render_overview():
    refresh_token = st.session_state["refresh_token"]
    logo_path = Path("assets/flipper_logo.png")
    top_left, top_mid, top_right = st.columns([1.2, 3, 2])

    if "show_new_order" not in st.session_state:
        st.session_state.show_new_order = False

    with top_left:
        st.image(str(logo_path), use_column_width=True)
    with top_mid:
        st.markdown(
            """
            <div style="padding-top:0.3rem;">
                <h1 style="margin-bottom:0;">Advanced Resell Analytics</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_right:
        if st.button("➕ Log New Order", use_container_width=True):
            st.session_state.show_new_order = not st.session_state.get("show_new_order", False)
        
        if st.session_state.get("order_saved_success"):
            st.success("✅ Order saved successfully!")
            st.session_state.order_saved_success = False

    if st.session_state.get("show_new_order", False):
        with st.expander("New Order", expanded=True):
            saved = render_new_order_form()
            if saved:
                st.session_state.show_new_order = False
                st.session_state.order_saved_success = True

                # force fresh data
                st.session_state.refresh_token += 1
                st.cache_data.clear()

                st.rerun()

    current_month_name = dt.date.today().strftime("%B %Y")
    st.header(f"Monthly Snapshot for {current_month_name}")

    current_month_kpi_df = get_current_month_kpi_df(st.session_state["refresh_token"])
    if current_month_kpi_df.empty:
        current_month_kpi_df = pd.DataFrame([{
            "items_sold": 0,
            "item_profit": 0
        }])
    
    row = current_month_kpi_df.iloc[0]
    items_sold = int(row.get("items_sold", 0) or 0)
    item_profit = float(row.get("item_profit", 0) or 0)

    col_left, col_empty = st.columns(2)
    
    with col_left:
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Items Sold", f"{items_sold}")
        with col_b:
            st.metric("Item Profit", f"${item_profit:,.2f}")

    with col_empty:
        pass


    # Monthly Revenue Chart
    st.altair_chart(get_monthly_profit_chart(st.session_state["refresh_token"]), use_container_width=True)

    st.markdown("---")

    st.header("All-Time Stats")

    col_01, col_02 = st.columns(2)
    with col_01:
        col_uno, col_dos = st.columns(2)
        with col_uno:
            items_sold_df = run_query_df("SELECT SUM(quantity) AS items_sold FROM sale_items", st.session_state["refresh_token"])
            items_sold = int(items_sold_df["items_sold"].iloc[0] or 0)
            st.metric("Items Sold", f"{items_sold}")
        with col_dos:
            total_profit_df = get_total_profit_df(st.session_state["refresh_token"])
            total_profit = float(total_profit_df["total_profit"].iloc[0] or 0)
            st.metric("Item Profit", f"${total_profit:,.2f}")

    with col_02:
        pass


    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recent Purchases")
        order_items_df = get_order_items_df(st.session_state["refresh_token"])
        st.dataframe(order_items_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cost (Per Unit)": st.column_config.NumberColumn("Cost (Per Unit)", format="$%.2f"),
            "Retail Value": st.column_config.NumberColumn("Retail Value", format="$%.2f"),
            "Date": st.column_config.DateColumn("Date",format="MM/DD/YY")
        })
        st.caption(f"Updated at: {dt.datetime.now()}")
    
    with col2:
        st.subheader("Recent Sales")
        sales_df = get_sales_df(st.session_state["refresh_token"])
        st.dataframe(sales_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
            "Date": st.column_config.DateColumn("Date",format="MM/DD/YY")
        })
        st.caption(f"Updated at: {dt.datetime.now()}")


    st.markdown("---")
    st.write("Use the sidebar to explore each table.")

render_overview()