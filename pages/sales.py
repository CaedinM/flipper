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

st.set_page_config(page_title="Sales", page_icon="🦭", layout="wide")

def render_sales():
    st.header("Sales")
    
    sales_df = get_sales_df(st.session_state["refresh_token"])
    
    left_col, right_col = st.columns(2)
    with left_col:
        col_1, col_2, col_3 = st.columns(3)
        with col_1:
            st.metric("Items Sold", sales_df["Number of Items"].sum())
        with col_2:
            total_revenue = sales_df["Revenue"].sum()
            st.metric("Total Revenue", f"${total_revenue:,.2f}")
        with col_3:
            avg_sale_price = sales_df["Revenue"].mean()
            st.metric("Average Sale Price", f"${avg_sale_price:,.2f}")
    with right_col:
        pass
        
    # Adjust column / primary key names if your sales schema is different
    df = run_query_df("SELECT * FROM sales ORDER BY sale_id LIMIT 500;", st.session_state["refresh_token"])
    st.dataframe(df, use_container_width=True)
    st.caption(f"Updated at: {dt.datetime.now()}")

render_sales()