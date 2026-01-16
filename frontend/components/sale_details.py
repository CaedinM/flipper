import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path for backend imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db import run_query_df

def render_sale_details(sale_id: int, refresh_token: int):
    """
    Display detailed information about a specific sale including items sold.
    
    Args:
        sale_id: The ID of the sale to display
        refresh_token: Token for cache refresh
    """
    # Get sale information
    sale_info = run_query_df(
        """
        SELECT 
            sale_id,
            sale_date,
            platform,
            sale_revenue
        FROM sales
        WHERE sale_id = %s
        """,
        refresh_token,
        (sale_id,)
    )
    
    if sale_info.empty:
        st.error(f"Sale ID {sale_id} not found.")
        return
    
    sale = sale_info.iloc[0]
    
    # Display sale header information
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sale Date", sale["sale_date"].strftime("%Y-%m-%d") if pd.notna(sale["sale_date"]) else "N/A")
    with col2:
        st.metric("Platform", sale["platform"] if pd.notna(sale["platform"]) else "N/A")
    with col3:
        st.metric("Total Revenue", f"${sale['sale_revenue']:,.2f}" if pd.notna(sale["sale_revenue"]) else "$0.00")
    
    st.divider()
    
    # Get sale items with item details and cost basis
    sale_items_df = run_query_df(
        """
        SELECT 
            si.quantity,
            si.unit_cost_basis_at_sale,
            i.description AS "Item Description",
            i.category AS "Category"
        FROM sale_items si
        JOIN items i ON si.item_id = i.item_id
        WHERE si.sale_id = %s
        ORDER BY i.description
        """,
        refresh_token,
        (sale_id,)
    )
    
    if sale_items_df.empty:
        st.info("No items found for this sale.")
    else:
        # Calculate item-level metrics
        sale_items_df["Total Cost"] = sale_items_df["quantity"] * sale_items_df["unit_cost_basis_at_sale"].fillna(0)
        
        # Calculate total cost basis and profit for the sale
        total_cost_basis = sale_items_df["Total Cost"].sum()
        total_profit = sale["sale_revenue"] - total_cost_basis
        
        # Display profit metric
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Cost Basis", f"${total_cost_basis:,.2f}")
        with col2:
            st.metric("Total Profit", f"${total_profit:,.2f}")
        
        st.divider()
        
        st.subheader("Items Sold")
        
        # Prepare display dataframe
        display_df = sale_items_df.copy()
        display_df["Unit Cost"] = display_df["unit_cost_basis_at_sale"]
        display_df = display_df[["Item Description", "Category", "quantity", "Unit Cost", "Total Cost"]]
        
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Item Description": st.column_config.TextColumn("Item Description"),
                "Category": st.column_config.TextColumn("Category"),
                "quantity": st.column_config.NumberColumn("Quantity", format="%d"),
                "Unit Cost": st.column_config.NumberColumn("Unit Cost", format="$%.2f"),
                "Total Cost": st.column_config.NumberColumn("Total Cost", format="$%.2f"),
            }
        )
        
        # Summary metrics
        total_items = sale_items_df["quantity"].sum()
        unique_items = len(sale_items_df)
        st.caption(f"Total items: {int(total_items)} | Unique items: {unique_items}")

