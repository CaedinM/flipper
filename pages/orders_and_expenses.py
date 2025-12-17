import streamlit as st
import pandas as pd
import altair as alt
import datetime as dt

from psycopg2.extras import execute_values
from pathlib import Path

from db import *
from charts import *
from components.new_order_form import render_new_order_form
from state import init_state


if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Orders and Expenses", page_icon="🦭", layout="wide")

def render_orders_and_expenses():
    order_items_df = get_order_items_df(st.session_state["refresh_token"])
    items_purchased = order_items_df["Quantity"].sum()
    total_spent = (order_items_df["Quantity"] * order_items_df["Cost (Per Unit)"]).sum()
    
    st.header("Orders and Expenses")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Items Purchased", f"{items_purchased}")
    with col_b:
        st.metric("Total Spent", f"${total_spent:,.2f}")

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
    st.dataframe(orders_df, use_container_width=True)

    expenses_df = run_query_df("SELECT * FROM other_expenses ORDER BY expense_date DESC;", st.session_state["refresh_token"])
    total_expenses = expenses_df['expense_cost'].sum()
    st.metric("Other Expenses", f"${total_expenses:,.2f}")
    st.dataframe(expenses_df, use_container_width=True)

render_orders_and_expenses()