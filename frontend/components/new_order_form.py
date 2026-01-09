import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
import sys
from pathlib import Path

# Add project root to path for backend imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import run_query_df, insert_order_with_items, upsert_item
from .utils import sanitize_order_num

def render_new_order_form():
    # Load item options with their categories
    items_df = run_query_df("""
        SELECT item_id, description, category
        FROM items
        ORDER BY description
    """)
    item_options = items_df["description"].tolist()
    description_to_id = dict(zip(items_df["description"], items_df["item_id"]))
    
    # Load existing categories from database
    categories_df = run_query_df("""
        SELECT DISTINCT category
        FROM items
        WHERE category IS NOT NULL AND category != ''
        ORDER BY category
    """)
    existing_categories = categories_df["category"].tolist() if not categories_df.empty else []
    # Add "Other" option for new categories
    category_options = existing_categories + ["Other"] if existing_categories else ["Other"]

    if "line_items_df" not in st.session_state:
        st.session_state.line_items_df = pd.DataFrame(
            [{"description": None, "category": None, "quantity": 1, "purchase_price_per_item": 0.0, "pas_fee_per_item": 0.0}]
        )

    with st.form("new_order_form", clear_on_submit=False): # Remove enter to submit when streamlit is upgraded
        st.subheader("Order Info")

        raw_order_num = st.text_input("Order #", placeholder="e.g., AMZ-12345")
        order_num = sanitize_order_num(raw_order_num)

        order_date = st.date_input("Order date", value=date.today())

        seller = st.selectbox(
            label="Platform / Retailer",
            options=["Target", "Walmart", "Pokemon Center", "Best Buy", "DICK's Sporting Goods", "LEGO Shop", "Other"]
        )

        total_cost = st.number_input(
            label="Total cost",
            min_value=0.0,
            max_value=99999999.99,
            step=0.01,
            label_visibility="visible",
            help="The total paid to the retailer including shipping and taxes. Do not include PAS_fees or any other additional expenses."
        )

        shipping_cost = st.number_input(
            label="Shipping Cost",
            min_value=0.0,
            max_value=99999999.99,
            step=0.01
        )

        st.subheader("Items")

        edited_df = st.data_editor(
            st.session_state.line_items_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "description": st.column_config.TextColumn(
                    "Item (description)",
                    help="Type to add a new item, or select from previously ordered items.",
                    required=True,
                ),
                "category": st.column_config.SelectboxColumn(
                    "Category",
                    options=category_options,
                    help="Select category for new items. Required for new items.",
                    required=False,
                ),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1),
                "purchase_price_per_item": st.column_config.NumberColumn("Price (Per Item)", min_value=0.00, step=0.01),
                "pas_fee_per_item": st.column_config.NumberColumn("PAS Fee (Per Item)", min_value=0.00, step=0.01),
            }
        )
        col_cancel, col_save = st.columns(2)
        with col_cancel:
            cancelled = st.form_submit_button("Cancel", type="primary", use_container_width=True)
        with col_save:
            submitted = st.form_submit_button("Save Order", type="primary", use_container_width=True)

    st.session_state.line_items_df = edited_df

    if cancelled:
        st.session_state.show_new_order = False
        st.rerun()

    if submitted:
        errors = []
        if not order_num.strip():
            errors.append("Order # is required.")
        if edited_df.empty:
            errors.append("Add at least one item to save order.")
        if (edited_df["quantity"] <= 0).any():
            errors.append("Quantities must be >= 1.")
        if (edited_df["description"].isna()).any():
            errors.append("Please enter an item description for every row.")
        
        # Check if new items have categories (allow "Other" which means no category)
        for idx, row in edited_df.iterrows():
            desc = row["description"]
            if pd.notna(desc) and desc.strip():
                desc = desc.strip()
                # If it's a new item (not in existing items), require category selection
                if desc not in description_to_id:
                    category = row.get("category")
                    if pd.isna(category) or not str(category).strip():
                        errors.append(f"Category is required for new item: '{desc}'. Please select a category (or 'Other' for no category).")

        if errors:
            for e in errors:
                st.error(e)
            return False

        try:
            items_to_insert = edited_df.copy()
            
            # Get or create item_ids for all descriptions
            # Handle both existing items and new items
            item_ids = []
            for idx, row in items_to_insert.iterrows():
                desc = row["description"]
                if pd.isna(desc) or not desc.strip():
                    raise ValueError("Item description cannot be empty.")
                
                desc = desc.strip()
                # Check if item exists
                if desc in description_to_id:
                    item_ids.append(description_to_id[desc])
                else:
                    # Get category for new item
                    category = row.get("category")
                    if pd.isna(category) or not str(category).strip() or str(category).strip() == "Other":
                        # If "Other" is selected or category is missing, use empty string
                        category_value = ""
                    else:
                        category_value = str(category).strip()
                    
                    # Create new item with category
                    new_item_id = upsert_item(description=desc, category=category_value if category_value else None)
                    item_ids.append(new_item_id)
                    # Update the mapping for potential duplicates in this order
                    description_to_id[desc] = new_item_id
            
            items_to_insert["item_id"] = item_ids
            
            insert_order_with_items(
                order_data={
                    "order_num": order_num.strip(),
                    "order_date": order_date,
                    "seller": seller,
                    "total_cost": total_cost,
                    "shipping_cost": shipping_cost,
                    "tax_rate": 0.0975 # HARD CODED TAX RATE FOR CALIFORNIA, IN FUTURE, LET USER SET LOCATION AND USE DICTIONARY TO SET TAX RATE
                },
                items_rows=items_to_insert[["item_id", "quantity", "purchase_price_per_item", "pas_fee_per_item"]].to_dict(orient="records")
                )
            
            st.success(f"Saved order {order_num} with {len(edited_df)} item(s).")
            st.session_state.line_items_df = pd.DataFrame(
                [{"description": None, "category": None, "quantity": 1, "purchase_price_per_item": 0.0, "pas_fee_per_item": 0.0}]
            )
            return True
        
        except psycopg2.errors.UniqueViolation:
            st.error("That Order # already exists.")
            return False
        except Exception as e:
            st.error(f"Failed to save order: {e}")
            return False