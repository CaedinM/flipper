import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db import get_profit_margin_by_category_df, get_profit_margin_by_platform_df, get_expense_breakdown_df
from frontend.components.theme import inject_theme
from frontend.state import init_state

if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Insights", layout="wide")
inject_theme()
st.title("Insights")

st.subheader("Cost Breakdown")

exp = get_expense_breakdown_df(st.session_state["refresh_token"])
if not exp.empty:
    row = exp.iloc[0]
    pas_fees   = float(row["total_pas_fees"] or 0)
    shipping   = float(row["total_shipping"] or 0)
    other      = float(row["total_other_expenses"] or 0)
    total_lost = pas_fees + shipping + other

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("PAS Fees",         f"${pas_fees:,.2f}")
    col2.metric("Shipping",         f"${shipping:,.2f}")
    col3.metric("Other Expenses",   f"${other:,.2f}")
    col4.metric("Total Lost",       f"${total_lost:,.2f}")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Profit Margin by Category")

    df = get_profit_margin_by_category_df(st.session_state["refresh_token"])

    if df.empty:
        st.info("No sales data yet.")
    else:
        st.dataframe(
            df.rename(columns={
                "category": "Category",
                "num_sales": "# Sales",
                "profit_margin": "Profit Margin (%)",
                "total_profit": "Total Profit",
                "total_revenue": "Total Revenue",
            }),
            hide_index=True,
            width="stretch",
            column_config={
                "Profit Margin (%)": st.column_config.NumberColumn("Profit Margin (%)", format="%.1f%%"),
                "Total Profit": st.column_config.NumberColumn("Total Profit", format="$%.2f"),
                "Total Revenue": st.column_config.NumberColumn("Total Revenue", format="$%.2f"),
            },
        )

with col_right:
    st.subheader("Profit Margin by Platform")

    platform_df = get_profit_margin_by_platform_df(st.session_state["refresh_token"])

    if platform_df.empty:
        st.info("No sales data yet.")
    else:
        st.dataframe(
            platform_df.rename(columns={
                "platform": "Platform",
                "num_sales": "# Sales",
                "profit_margin": "Profit Margin (%)",
                "total_profit": "Total Profit",
                "total_revenue": "Total Revenue",
            }),
            hide_index=True,
            width="stretch",
            column_config={
                "Profit Margin (%)": st.column_config.NumberColumn("Profit Margin (%)", format="%.1f%%"),
                "Total Profit": st.column_config.NumberColumn("Total Profit", format="$%.2f"),
                "Total Revenue": st.column_config.NumberColumn("Total Revenue", format="$%.2f"),
            },
        )
