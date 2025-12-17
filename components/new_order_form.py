import streamlit as st
import pandas as pd
from datetime import date
import psycopg2

from db import run_query_df, insert_order_with_items
from utils import sanitize_order_num

def render_new_order_form():
    # Load item options
    items_df = run_query_df("""
        SELECT item_id, description
        FROM items
        ORDER BY description
    """)
    item_options = items_df["description"].tolist()
    description_to_id = dict(zip(items_df["description"], items_df["item_id"]))

    if "line_items_df" not in st.session_state:
        st.session_state.line_items_df = pd.DataFrame(
            [{"description": None, "quantity": 1, "purchase_price_per_item": 0.0, "pas_fee_per_item": 0.0}]
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
                "description": st.column_config.SelectboxColumn(
                    "Item (description)",
                    options=item_options,
                    help="Select from previously ordered items",
                    ),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1),
                "purchase_price_per_item": st.column_config.NumberColumn("Price (Per Item)", min_value=0.00, step=0.01),
                "pas_fee_per_item": st.column_config.NumberColumn("PAS Fee (Per Item)", min_value=0.00, step=0.01),
            }
        )

        submitted = st.form_submit_button("Save Order", type="primary", use_container_width=True)

    st.session_state.line_items_df = edited_df

    if submitted:
        errors = []
        if not order_num.strip():
            errors.append("Order # is required.")
        if edited_df.empty:
            errors.append("Add at least one item to save order.")
        if (edited_df["quantity"] <= 0).any():
            errors.append("Quantities must be >= 1.")
        if (edited_df["description"].isna()).any():
            errors.append("Please select an item for every row.")

        if errors:
            for e in errors:
                st.error(e)
            return False

        try:
            # DEBUGGING
            st.write("DEBUG: line_items_df")
            st.write(st.session_state.line_items_df)

            st.write("DEBUG: line_items_df columns")
            st.write(st.session_state.line_items_df.columns.tolist())

            st.write("DEBUG: selected items")
            st.write(st.session_state.line_items_df.to_dict(orient="records"))

            items_to_insert = edited_df.copy()
            items_to_insert["item_id"] = items_to_insert["description"].map(description_to_id)
            
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
                [{"description": None, "quantity": 1, "purchase_price_per_item": 0.0, "pas_fee_per_item": 0.0}]
            )
            return True
        
        except psycopg2.errors.UniqueViolation:
            st.error("That Order # already exists.")
            return False
        except Exception as e:
            st.error(f"Failed to save order: {e}")
            return False