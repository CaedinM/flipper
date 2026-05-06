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
from frontend.components.theme import inject_theme
from frontend.state import init_state


if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Inventory", page_icon="🦭", layout="wide")

def render_inventory():
    inject_theme()
    st.header("Inventory")

    inventory_df = get_inventory_df(st.session_state["refresh_token"])

    total_units = int(inventory_df["Stock"].sum())
    unique_items_in_stock = len(inventory_df[inventory_df["Stock"] > 0])
    stock_by_category = inventory_df.groupby("Category")["Stock"].sum()
    top_category = stock_by_category.idxmax() if not stock_by_category.empty else "—"

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Units in Stock", total_units)
    col2.metric("Unique Items in Stock", unique_items_in_stock)
    col3.metric("Top Category in Stock", top_category)

    st.markdown("---")

    categories = sorted(inventory_df["Category"].dropna().unique())
    for category in categories:
        cat_df = inventory_df[inventory_df["Category"] == category].copy()
        if cat_df.empty:
            continue

        total_stock = int(cat_df["Stock"].sum())
        st.subheader(f"{category} ({total_stock} units)")

        display_df = cat_df.drop(columns=["item_id", "Category"], errors="ignore")

        if category == "Pokemon" and {"Era", "Set", "Product"}.issubset(display_df.columns):
            display_df.insert(0, "Description", display_df["Set"].fillna("") + " – " + display_df["Product"].fillna(""))
            display_df = display_df.drop(columns=["Set", "Product"])
        elif {"Era", "Set", "Product"}.issubset(display_df.columns):
            display_df = display_df.rename(columns={"Product": "Description"})
            display_df = display_df.drop(columns=["Era", "Set"], errors="ignore")

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Description": st.column_config.TextColumn("Description"),
                "Cost Basis": st.column_config.NumberColumn("Cost Basis", format="$%.2f"),
            },
        )

    st.caption(f"Updated at: {dt.datetime.now()}")

render_inventory()