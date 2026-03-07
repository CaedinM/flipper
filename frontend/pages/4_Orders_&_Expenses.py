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
from frontend.components.add_pas_fee_form import render_add_pas_fee_form
from frontend.state import init_state


if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Orders and Expenses", page_icon="🦭", layout="wide")

def render_orders_and_expenses():
    order_items_df = get_order_items_df(st.session_state["refresh_token"])
    items_purchased = order_items_df["Quantity"].sum()
    total_spent = (order_items_df["Quantity"] * order_items_df["Cost (Per Unit)"]).sum()
    
    st.header("Orders and Expenses")
    
    # Top section with metrics and PAS fee form
    col_a, col_b = st.columns([2, 1])
    with col_a:
        col_metric_1, col_metric_2 = st.columns(2)
        with col_metric_1:
            st.metric("Items Purchased", f"{items_purchased}")
        with col_metric_2:
            st.metric("Total Spent", f"${total_spent:,.2f}")
    with col_b:
        # Initialize session state for PAS fee form
        if "show_add_pas_fee" not in st.session_state:
            st.session_state.show_add_pas_fee = False
        
        if st.button("➕ Add/Update PAS Fees", width="stretch", key="show_pas_fee_btn"):
            st.session_state.show_add_pas_fee = not st.session_state.get("show_add_pas_fee", False)
        
        if st.session_state.get("pas_fee_saved_success"):
            st.success("✅ PAS fees updated successfully!")
            st.session_state.pas_fee_saved_success = False
    
    # Show PAS fee form if button was clicked
    if st.session_state.get("show_add_pas_fee", False):
        with st.expander("Add/Update PAS Fees", expanded=True):
            saved = render_add_pas_fee_form()
            if saved:
                st.session_state.show_add_pas_fee = False
                st.session_state.pas_fee_saved_success = True
                
                # Force fresh data
                st.session_state.refresh_token += 1
                st.cache_data.clear()
                
                st.rerun()

    st.subheader("Order History")
    st.caption(f"Updated at: {dt.datetime.now()}")
    orders_df = run_query_df("SELECT * FROM orders ORDER BY order_date DESC LIMIT 500;", st.session_state["refresh_token"])
    orders_df = orders_df.rename(columns={
        "order_num": "Order Number",
        "order_date": "Order Date",
        "seller": "Seller",
        "total_cost": "Total Cost",
        "shipping_cost": "Shipping Cost",
        "tax_rate": "Tax Rate"
        })
    orders_df["Tax Rate"] = orders_df["Tax Rate"] * 100
    st.dataframe(orders_df, width="stretch")

    expenses_df = run_query_df("SELECT * FROM other_expenses ORDER BY expense_date DESC;", st.session_state["refresh_token"])
    total_expenses = expenses_df['expense_cost'].sum()
    st.metric("Other Expenses", f"${total_expenses:,.2f}")
    st.dataframe(expenses_df, width="stretch")

render_orders_and_expenses()