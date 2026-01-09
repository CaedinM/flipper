import streamlit as st
import pandas as pd
import altair as alt
import datetime as dt
import sys
from pathlib import Path

from psycopg2.extras import execute_values

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db import *
from frontend.components.charts import *
from frontend.components.new_order_form import render_new_order_form
from frontend.state import init_state


if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Inventory", page_icon="🦭", layout="wide")

def render_inventory():
    st.header("Inventory")
    col1, col2, col3, col4 = st.columns(4)
    
    st.subheader("Current Invetory") # INVENTORY TABLE
    inventory_df = get_inventory_df(st.session_state["refresh_token"])
    st.dataframe(inventory_df, use_container_width=True, hide_index=True,
    column_config={
        "Retail Value": st.column_config.NumberColumn(
            "Retail Value",
            format="%.2f"
        )
    }
    )
    st.caption(f"Updated at: {dt.datetime.now()}")

    total_units = int(inventory_df["Stock"].sum())
    total_retail_value = float((inventory_df["Retail Value"] * inventory_df["Stock"]).sum())
    unique_items_in_stock = len(inventory_df[inventory_df["Stock"] > 0])
    stock_by_category = inventory_df.groupby("Category")["Stock"].sum()
    top_category = stock_by_category.idxmax()
    
    col1.metric("Total Units in Stock", total_units)
    col2.metric("Total Retail Value", f"${total_retail_value:,.2f}")
    col3.metric("Unique Items in Stock", unique_items_in_stock)
    col4.metric("Top Category in Stock", top_category)

render_inventory()