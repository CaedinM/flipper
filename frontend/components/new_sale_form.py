import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
import sys
from pathlib import Path

# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import run_query_df, insert_sale_with_items, upsert_item, get_inventory_df

def render_new_sale_form():
    # Load item options with their categories (only items in stock)
    # Use get_inventory_df to get items in stock, then join with items table to get item_id
    inventory_df = get_inventory_df(0)  # Use refresh_token 0 for initial load
    
    # Get item_ids for items in inventory by matching descriptions
    if not inventory_df.empty:
        # Get descriptions from inventory
        item_descriptions = inventory_df["Item"].tolist()
        # Create parameterized query
        placeholders = ','.join(['%s'] * len(item_descriptions))
        items_df = run_query_df(
            f"""
            SELECT i.item_id, i.description, i.category
            FROM items i
            WHERE i.description IN ({placeholders})
            ORDER BY i.description
            """,
            0,
            tuple(item_descriptions)
        )
    else:
        items_df = pd.DataFrame(columns=["item_id", "description", "category"])
    item_options = items_df["description"].tolist()
    description_to_id = dict(zip(items_df["description"], items_df["item_id"]))
    
    if "sale_line_items_df" not in st.session_state:
        st.session_state.sale_line_items_df = pd.DataFrame(
            [{"description": None, "quantity": 1}]
        )

    with st.form("new_sale_form", clear_on_submit=False):
        st.subheader("Sale Info")

        sale_date = st.date_input("Sale date", value=date.today())

        platform = st.selectbox(
            label="Platform",
            options=["eBay", "OfferUp", "Facebook Marketplace", "Poshmark", "Other"]
        )

        sale_revenue = st.number_input(
            label="Sale Revenue",
            min_value=0.0,
            max_value=99999999.99,
            step=0.01,
            label_visibility="visible",
            help="Total revenue received from this sale."
        )

        st.subheader("Items Sold")

        edited_df = st.data_editor(
            st.session_state.sale_line_items_df,
            num_rows="dynamic",
            width="stretch",
            column_config={
                "description": st.column_config.SelectboxColumn(
                    "Item (description)",
                    options=item_options,
                    help="Select an item to sell. Only items in inventory are listed.",
                    required=True,
                ),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1),
            }
        )
        col_cancel, col_save = st.columns(2)
        with col_cancel:
            cancelled = st.form_submit_button("Cancel", type="primary", width="stretch")
        with col_save:
            submitted = st.form_submit_button("Save Sale", type="primary", width="stretch")

    st.session_state.sale_line_items_df = edited_df

    if cancelled:
        st.session_state.show_new_sale = False
        st.rerun()

    if submitted:
        # Normalize columns — data_editor can return lists in some edge cases
        edited_df = edited_df.copy()
        edited_df["description"] = edited_df["description"].apply(
            lambda x: x[0] if isinstance(x, list) and x else (None if isinstance(x, list) else x)
        )
        errors = []
        if edited_df.empty:
            errors.append("Add at least one item to save sale.")
        if (edited_df["quantity"] <= 0).any():
            errors.append("Quantities must be >= 1.")
        if (edited_df["description"].isna()).any():
            errors.append("Please enter an item description for every row.")
        if sale_revenue <= 0:
            errors.append("Sale revenue must be greater than 0.")

        if errors:
            for e in errors:
                st.error(e)
            return False

        try:
            items_to_insert = edited_df.copy()
            
            # Get or create item_ids for all descriptions
            # Since items come from inventory dropdown, they should all exist
            item_ids = []
            for idx, row in items_to_insert.iterrows():
                desc = row["description"]
                if pd.isna(desc) or not str(desc).strip():
                    raise ValueError("Item description cannot be empty.")
                
                desc = str(desc).strip()
                # Check if item exists in our mapping (should always be true for dropdown items)
                if desc in description_to_id:
                    item_ids.append(description_to_id[desc])
                else:
                    # This shouldn't happen with dropdown, but handle it gracefully
                    st.warning(f"Item '{desc}' not found in inventory. Attempting to find or create...")
                    try:
                        # Try to find the item in the database
                        existing_item = run_query_df(
                            "SELECT item_id FROM items WHERE description = %s",
                            0,
                            (desc,)
                        )
                        if not existing_item.empty:
                            item_id = int(existing_item.iloc[0]["item_id"])
                            item_ids.append(item_id)
                            description_to_id[desc] = item_id
                        else:
                            # Item doesn't exist - this shouldn't happen with inventory items
                            raise ValueError(f"Item '{desc}' is not in inventory and cannot be sold.")
                    except Exception as e:
                        st.error(f"Error finding item '{desc}': {e}")
                        return False
            
            if len(item_ids) != len(items_to_insert):
                raise ValueError(f"Mismatch: {len(item_ids)} item IDs for {len(items_to_insert)} items")
            
            items_to_insert["item_id"] = item_ids
            
            # Validate that all item_ids are valid integers
            if any(pd.isna(item_id) or item_id is None for item_id in item_ids):
                raise ValueError("One or more items have invalid item_id")
            
            # Prepare items_rows for insertion
            items_rows = items_to_insert[["item_id", "quantity"]].to_dict(orient="records")
            
            # Ensure all values are proper types
            for row in items_rows:
                row["item_id"] = int(row["item_id"])
                row["quantity"] = int(row["quantity"])
            
            insert_sale_with_items(
                sale_data={
                    "sale_date": sale_date,
                    "platform": platform,
                    "sale_revenue": float(sale_revenue)
                },
                items_rows=items_rows
                )
            
            st.success(f"Saved sale with {len(edited_df)} item(s) for ${sale_revenue:,.2f}.")
            st.session_state.sale_line_items_df = pd.DataFrame(
                [{"description": None, "quantity": 1}]
            )
            return True
        
        except psycopg2.errors.UniqueViolation as e:
            st.error(f"Database constraint violation: {e}")
            import traceback
            st.exception(e)
            return False
        except psycopg2.errors.DatabaseError as e:
            st.error(f"Database error: {e}")
            import traceback
            st.exception(e)
            return False
        except Exception as e:
            st.error(f"Failed to save sale: {e}")
            import traceback
            st.exception(e)  # This will show the full traceback in Streamlit
            return False

