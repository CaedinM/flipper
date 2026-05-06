import streamlit as st
import pandas as pd
import psycopg2
import sys
from pathlib import Path

# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import run_query_df, get_order_items_by_order_num, update_pas_fees_for_order

def render_add_pas_fee_form():
    """
    Form component to add/update PAS fees for items in an existing order.
    """
    # Load all orders for selection
    orders_df = run_query_df(
        """
        SELECT 
            order_num,
            order_date,
            seller
        FROM orders
        ORDER BY order_date DESC, order_num DESC
        LIMIT 500
        """,
        0
    )
    
    if orders_df.empty:
        st.warning("No orders found. Please create an order first.")
        return False
    
    # Initialize session state for selected order
    if "selected_order_num_pas" not in st.session_state:
        st.session_state.selected_order_num_pas = None
    
    st.subheader("Select Order")
    
    # Create order display options
    order_options = [
        f"{row['order_num']} - {row['order_date']} - {row['seller']}"
        for _, row in orders_df.iterrows()
    ]
    order_nums = orders_df["order_num"].tolist()
    
    selected_index = st.selectbox(
        "Select an order to add/update PAS fees:",
        options=range(len(order_options)),
        format_func=lambda x: order_options[x],
        index=None,
        key="pas_fee_order_selector"
    )
    
    if selected_index is not None:
        st.session_state.selected_order_num_pas = order_nums[selected_index]
    else:
        st.session_state.selected_order_num_pas = None
    
    # Load order items if order is selected
    if st.session_state.selected_order_num_pas:
        order_items_df = get_order_items_by_order_num(
            st.session_state.selected_order_num_pas,
            0
        )
        
        if order_items_df.empty:
            st.warning(f"No items found for order {st.session_state.selected_order_num_pas}.")
            return False
        
        st.divider()
        st.subheader(f"Order: {st.session_state.selected_order_num_pas}")
        
        order_items_df["Description"] = order_items_df["Set"].fillna("") + " – " + order_items_df["Product"].fillna("")
        edit_df = order_items_df[[
            "Description",
            "Era",
            "Category",
            "Quantity",
            "Price Tag",
            "PAS Fee Per Item",
            "Cost Basis"
        ]].copy()

        with st.form("add_pas_fee_form", clear_on_submit=False):

            edited_df = st.data_editor(
                edit_df,
                width="stretch",
                hide_index=True,
                disabled=["Description", "Era", "Category", "Quantity", "Price Tag", "Cost Basis"],
                column_config={
                    "Description": st.column_config.TextColumn("Description"),
                    "Era": st.column_config.TextColumn("Era"),
                    "Category": st.column_config.TextColumn("Category"),
                    "Quantity": st.column_config.NumberColumn("Quantity", format="%d"),
                    "Price Tag": st.column_config.NumberColumn("Price Tag", format="$%.2f"),
                    "PAS Fee Per Item": st.column_config.NumberColumn(
                        "PAS Fee Per Item",
                        min_value=0.00,
                        step=0.01,
                        format="$%.2f",
                        help="Enter the PAS (Purchase Assistance Service) fee per item"
                    ),
                    "Cost Basis": st.column_config.NumberColumn("Cost Basis", format="$%.2f"),
                }
            )
            
            col_cancel, col_save = st.columns(2)
            with col_cancel:
                cancelled = st.form_submit_button("Cancel", type="secondary", width="stretch")
            with col_save:
                submitted = st.form_submit_button("Save PAS Fees", type="primary", width="stretch")
            
            if cancelled:
                st.session_state.selected_order_num_pas = None
                if "pas_fee_order_selector" in st.session_state:
                    del st.session_state.pas_fee_order_selector
                st.rerun()
            
            if submitted:
                # Validate inputs
                errors = []
                if (edited_df["PAS Fee Per Item"] < 0).any():
                    errors.append("PAS fees cannot be negative.")
                
                if errors:
                    for e in errors:
                        st.error(e)
                    return False
                
                try:
                    order_item_ids = order_items_df["order_item_id"].tolist()
                    pas_fee_updates = [
                        {
                            "order_item_id": int(order_item_ids[i]),
                            "pas_fee_per_item": float(row["PAS Fee Per Item"])
                        }
                        for i, (_, row) in enumerate(edited_df.iterrows())
                    ]
                    
                    # Update database
                    update_pas_fees_for_order(
                        st.session_state.selected_order_num_pas,
                        pas_fee_updates
                    )
                    
                    st.success(f"Successfully updated PAS fees for order {st.session_state.selected_order_num_pas}.")
                    st.session_state.selected_order_num_pas = None
                    if "pas_fee_order_selector" in st.session_state:
                        del st.session_state.pas_fee_order_selector
                    return True
                
                except psycopg2.errors.DatabaseError as e:
                    st.error(f"Database error: {e}")
                    st.exception(e)
                    return False
                except Exception as e:
                    st.error(f"Failed to update PAS fees: {e}")
                    st.exception(e)
                    return False
    else:
        st.info("Please select an order to continue.")
    
    return False
