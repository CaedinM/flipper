import streamlit as st
import pandas as pd
import datetime as dt
import sys
from pathlib import Path

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db import *
from frontend.components.charts import *
from frontend.components.sale_details import render_sale_details
from frontend.components.theme import inject_theme
from frontend.state import init_state


if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Sales", page_icon="🦭", layout="wide")

def render_sales():
    inject_theme()
    st.header("Sales")
    
    sales_df = get_sales_df(st.session_state["refresh_token"])
    
    col_1, col_2, col_3 = st.columns(3)
    with col_1:
        st.metric("Items Sold", sales_df["Number of Items"].sum())
    with col_2:
        total_revenue = sales_df["Revenue"].sum()
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    with col_3:
        avg_sale_price = sales_df["Revenue"].mean()
        st.metric("Average Sale Price", f"${avg_sale_price:,.2f}")
    
    # Get sales data with sale_id for selection, including cost basis from sale_items
    df = run_query_df(
        """
        SELECT 
            s.sale_id,
            s.sale_date AS "Date",
            s.platform AS "Platform",
            s.sale_revenue AS "Revenue",
            COALESCE(SUM(si.quantity * si.unit_cost_basis_at_sale), 0) AS "Cost Basis"
        FROM sales s
        LEFT JOIN sale_items si ON si.sale_id = s.sale_id
        GROUP BY s.sale_id, s.sale_date, s.platform, s.sale_revenue
        ORDER BY s.sale_date DESC, s.sale_id DESC
        LIMIT 500
        """, 
        st.session_state["refresh_token"]
    )
    
    # Initialize selected sale in session state
    if "selected_sale_id" not in st.session_state:
        st.session_state.selected_sale_id = None
    
    # Display sales table with selection
    st.subheader("Sales History")
    
    # Create a formatted dataframe for display
    display_df = df.copy()
    if "Cost Basis" in display_df.columns and not display_df["Cost Basis"].isna().all():
        display_df["Profit"] = display_df["Revenue"] - display_df["Cost Basis"].fillna(0)
        display_df = display_df[["Date", "Platform", "Revenue", "Cost Basis", "Profit", "sale_id"]]
    else:
        display_df = display_df[["Date", "Platform", "Revenue", "sale_id"]]
    
    # Add a "View Details" column with buttons
    display_df_display = display_df.copy()
    if "sale_id" in display_df_display.columns:
        display_df_display = display_df_display.drop(columns=["sale_id"])
    
    # Use data_editor with selection mode for clickable rows
    edited_df = st.data_editor(
        display_df_display,
        width="stretch",
        hide_index=True,
        disabled=True,  # Make it read-only
        column_config={
            "Date": st.column_config.DateColumn("Date", format="MM/DD/YY"),
            "Revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
            "Cost Basis": st.column_config.NumberColumn("Cost Basis", format="$%.2f") if "Cost Basis" in display_df_display.columns else None,
            "Profit": st.column_config.NumberColumn("Profit", format="$%.2f") if "Profit" in display_df_display.columns else None,
        }
    )
    
    # Add selection interface using selectbox
    st.subheader("View Sale Details")
    sale_options = [f"Sale #{row['sale_id']} - {row['Date']} - {row['Platform']} - ${row['Revenue']:,.2f}" 
                    for _, row in df.iterrows()]
    sale_ids = df["sale_id"].tolist()
    
    if sale_options:
        selected_index = st.selectbox(
            "Select a sale to view details:",
            options=range(len(sale_options)),
            format_func=lambda x: sale_options[x],
            index=None,
            key="sale_selector"
        )
        
        if selected_index is not None:
            st.session_state.selected_sale_id = int(sale_ids[selected_index])
    
    # Show sale details if a sale is selected
    if st.session_state.selected_sale_id:
        st.divider()
        with st.expander(f"Sale Details - Sale ID: {st.session_state.selected_sale_id}", expanded=True):
            render_sale_details(st.session_state.selected_sale_id, st.session_state["refresh_token"])
            if st.button("Close Details", key="close_sale_details"):
                st.session_state.selected_sale_id = None
                # Clear the selectbox selection
                if "sale_selector" in st.session_state:
                    del st.session_state.sale_selector
                st.rerun()
    
    st.caption(f"Updated at: {dt.datetime.now()}")

render_sales()