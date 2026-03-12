import streamlit as st
import pandas as pd
import datetime as dt
import sys
from pathlib import Path
# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import *
from components.charts import *
from components.new_order_form import render_new_order_form
from components.new_sale_form import render_new_sale_form
from components.theme import inject_theme
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
    inject_theme()
    refresh_token = st.session_state["refresh_token"]
    # Get absolute path to logo (assets folder is in frontend directory)
    frontend_dir = Path(__file__).parent
    logo_path = frontend_dir / "assets" / "flipper_logo.png"
    top_left, top_mid, top_right = st.columns([1.2, 3, 2])

    if "show_new_order" not in st.session_state:
        st.session_state.show_new_order = False
    if "show_new_sale" not in st.session_state:
        st.session_state.show_new_sale = False

    with top_left:
        st.image(str(logo_path), width="stretch")
    with top_mid:
        st.markdown(
            """
            <div style="padding-top:0.4rem;">
                <div style="font-family:'Chakra Petch',monospace;font-size:0.6rem;font-weight:600;
                            letter-spacing:0.35em;text-transform:uppercase;color:#5A8070;
                            margin-bottom:0.3rem;">
                    ◆ RESELL ANALYTICS PLATFORM
                </div>
                <h1 style="margin:0;font-family:'Chakra Petch',monospace;font-weight:700;
                            font-size:2rem;letter-spacing:0.05em;text-transform:uppercase;
                            color:#E2EDD8;">
                    FLIPPER
                    <span style="color:#C8FF00;">.</span>
                </h1>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_right:
        if st.button("➕ Log New Order", width="stretch"):
            st.session_state.show_new_order = not st.session_state.get("show_new_order", False)
            st.session_state.show_new_sale = False  # Close sale form if open
        
        if st.button("💰 Log New Sale", width="stretch"):
            st.session_state.show_new_sale = not st.session_state.get("show_new_sale", False)
            st.session_state.show_new_order = False  # Close order form if open
        
        if st.session_state.get("order_saved_success"):
            st.success("✅ Order saved successfully!")
            st.session_state.order_saved_success = False
        
        if st.session_state.get("sale_saved_success"):
            st.success("✅ Sale saved successfully!")
            st.session_state.sale_saved_success = False

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

    if st.session_state.get("show_new_sale", False):
        with st.expander("New Sale", expanded=True):
            saved = render_new_sale_form()
            if saved:
                st.session_state.show_new_sale = False
                st.session_state.sale_saved_success = True

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


    # Monthly Charts
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.altair_chart(get_monthly_profit_chart(st.session_state["refresh_token"]), width="stretch")
    with chart_col2:
        st.altair_chart(get_monthly_items_sold_chart(st.session_state["refresh_token"]), width="stretch")

    st.markdown("---")

    st.header("All-Time Stats")

    # Row 1: Items Sold | Item Profit | Net Profit | Avg Profit Margin
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    with row1_col1:
        items_sold_df = run_query_df("SELECT SUM(quantity) AS items_sold FROM sale_items", st.session_state["refresh_token"])
        items_sold = int(items_sold_df["items_sold"].iloc[0] or 0)
        st.metric("Items Sold", f"{items_sold}")
    with row1_col2:
        total_profit_df = get_total_profit_df(st.session_state["refresh_token"])
        total_profit = float(total_profit_df["total_profit"].iloc[0] or 0)
        st.metric("Item Profit", f"${total_profit:,.2f}")
    with row1_col3:
        net_profit_df = get_net_profit_df(st.session_state["refresh_token"])
        net_profit = float(net_profit_df["net_profit"].iloc[0] or 0)
        st.metric("Net Profit", f"${net_profit:,.2f}")
    with row1_col4:
        margin_df = get_avg_profit_margin_df(st.session_state["refresh_token"])
        avg_margin = float(margin_df["avg_profit_margin"].iloc[0] or 0)
        st.metric("Avg Profit Margin", f"{avg_margin:.1f}%")

    # Row 2: Inventory Count | Inventory Value | Sales Velocity | {blank}
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        inventory_count_df = get_inventory_count_df(st.session_state["refresh_token"])
        inventory_count = int(inventory_count_df["inventory_count"].iloc[0] or 0)
        st.metric("Inventory Count", f"{inventory_count}")
    with row2_col2:
        inventory_value_df = get_inventory_value_df(st.session_state["refresh_token"])
        inventory_value = float(inventory_value_df["inventory_value"].iloc[0] or 0)
        st.metric("Inventory Value", f"${inventory_value:,.2f}")
    with row2_col3:
        sales_velocity_df = get_sales_velocity_df(st.session_state["refresh_token"])
        sales_velocity = float(sales_velocity_df["items_per_week"].iloc[0] or 0)
        st.metric("Sales Velocity", f"{sales_velocity:.2f} /week")


    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recent Purchases")
        order_items_df = get_order_items_df(st.session_state["refresh_token"])
        order_items_df = order_items_df.sort_values(by="Date", ascending=False)
        st.dataframe(order_items_df,
        width="stretch",
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
        sales_df = sales_df.sort_values(by="Date", ascending=False)
        st.dataframe(sales_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
            "Date": st.column_config.DateColumn("Date",format="MM/DD/YY")
        })
        st.caption(f"Updated at: {dt.datetime.now()}")


    st.markdown("---")
    st.write("Use the sidebar to explore each table.")

render_overview()