import streamlit as st
import pandas as pd
import altair as alt
import datetime as dt

from psycopg2.extras import execute_values
from pathlib import Path

from db import *
from charts import monthly_profit_chart
from components.new_order_form import render_new_order_form


# Page config
st.set_page_config(
    page_title="Flipper - Resell Analytics Platform",
    page_icon="🦭",  # you can swap this for your logo favicon later
    layout="wide"
)

# ################################################################################
# HEADER FORMATING
# ################################################################################
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
        st.session_state.show_new_order = not st.session_state.show_new_order
    if st.session_state.get("order_saved_success"):
        st.success("✅ Order saved successfully!")
        st.session_state.order_saved_success = False

if st.session_state.show_new_order:
    with st.expander("New Order", expanded=True):
        saved = render_new_order_form()
        if saved:
            st.session_state.show_new_order = False
            st.session_state.order_saved_success = True 
            st.rerun()


# ################################################################################
# SIDEBAR FORMATTING
# ################################################################################
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Overview", "Inventory", "Sales", "Orders & Expenses"],
)


# ################################################################################
# PAGES
# ################################################################################

# Overview page
if page == "Overview":

    current_month_name = dt.date.today().strftime("%B %Y")
    st.header(f"Monthly Snapshot for {current_month_name}")

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
    st.altair_chart(monthly_profit_chart, use_container_width=True)

    st.markdown("---")

    st.header("All-Time Stats")

    col_01, col_02 = st.columns(2)
    with col_01:
        col_uno, col_dos = st.columns(2)
        with col_uno:
            items_sold_df = run_query("SELECT SUM(quantity) AS items_sold FROM sale_items")
            items_sold = int(items_sold_df["items_sold"].iloc[0] or 0)
            st.metric("Items Sold", f"{items_sold}")
        with col_dos:
            total_profit = float(total_profit_df["total_profit"].iloc[0] or 0)
            st.metric("Item Profit", f"${total_profit:,.2f}")

    with col_02:
        pass


    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recent Purchases")
        st.dataframe(order_items_df, use_container_width=True, hide_index=True,
        column_config={
            "Cost (Per Unit)": st.column_config.NumberColumn("Cost (Per Unit)", format="$%.2f"),
            "Retail Value": st.column_config.NumberColumn("Retail Value", format="$%.2f"),
            "Date": st.column_config.DateColumn("Date",format="MM/DD/YY")
        })
    
    with col2:
        st.subheader("Recent Sales")
        st.dataframe(sales_df, use_container_width=True, hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
            "Date": st.column_config.DateColumn("Date",format="MM/DD/YY")
        })


    st.markdown("---")
    st.write("Use the sidebar to explore each table.")

# Items page
elif page == "Items":
    st.subheader("Items")
    df = run_query("SELECT * FROM items ORDER BY item_id LIMIT 500;")
    st.dataframe(df, use_container_width=True)

# Orders and Expenses page
elif page == "Orders & Expenses":
    items_purchased = order_items_df["Quantity"].sum()
    total_spent = (order_items_df["Quantity"] * order_items_df["Cost (Per Unit)"]).sum()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Items Purchased", f"{items_purchased}")
    with col_b:
        st.metric("Total Spent", f"${total_spent:,.2f}")

    st.subheader("Order History")
    orders_df = run_query("SELECT * FROM orders ORDER BY order_date DESC LIMIT 500;")
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

    expenses_df = run_query("SELECT * FROM other_expenses ORDER BY expense_date DESC;")
    total_expenses = expenses_df['expense_cost'].sum()
    st.metric("Other Expenses", f"${total_expenses:,.2f}")
    st.dataframe(expenses_df, use_container_width=True)

# Order Items page
elif page == "Order Items":
    st.subheader("Order Items")
    df = run_query("SELECT * FROM order_items ORDER BY order_item_id LIMIT 500;")
    st.dataframe(df, use_container_width=True)

# Sales page
elif page == "Sales":
    st.header("Sales")

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
    df = run_query("SELECT * FROM sales ORDER BY sale_id LIMIT 500;")
    st.dataframe(df, use_container_width=True)

# Returns page
elif page == "Returns":
    st.subheader("Returns")
    df = run_query("SELECT * FROM returns ORDER BY return_id LIMIT 500;")
    st.dataframe(df, use_container_width=True)

# Inventory page
elif page == "Inventory":
    st.header("Inventory")

    st.subheader("Overview:") # OVERVIEW
    col1, col2, col3, col4 = st.columns(4)

    st.subheader("Current Invetory") # INVENTORY TABLE

    st.dataframe(inventory_df, use_container_width=True, hide_index=True,
    column_config={
        "Retail Value": st.column_config.NumberColumn(
            "Retail Value",
            format="%.2f"
        )
    })

    total_units = int(inventory_df["Stock"].sum())
    total_retail_value = float((inventory_df["Retail Value"] * inventory_df["Stock"]).sum())
    unique_items_in_stock = len(inventory_df[inventory_df["Stock"] > 0])
    stock_by_category = inventory_df.groupby("Category")["Stock"].sum()
    top_category = stock_by_category.idxmax()
    
    col1.metric("Total Units in Stock", total_units)
    col2.metric("Total Retail Value", f"${total_retail_value:,.2f}")
    col3.metric("Unique Items in Stock", unique_items_in_stock)
    col4.metric("Top Category in Stock", top_category)
