import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import run_query_df, insert_sale_with_items, get_inventory_df

def render_new_sale_form():
    inventory_df = get_inventory_df(0)

    if not inventory_df.empty:
        inventory_df["label"] = inventory_df["Set"] + " – " + inventory_df["Product"]
        item_options = inventory_df["label"].tolist()
        label_to_id = dict(zip(inventory_df["label"], inventory_df["item_id"]))
    else:
        item_options = []
        label_to_id = {}

    if "sale_line_items_df" not in st.session_state:
        st.session_state.sale_line_items_df = pd.DataFrame(
            [{"item": None, "quantity": 1}]
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
            help="Total revenue received from this sale."
        )

        st.subheader("Items Sold")

        edited_df = st.data_editor(
            st.session_state.sale_line_items_df,
            num_rows="dynamic",
            width="stretch",
            column_config={
                "item": st.column_config.SelectboxColumn(
                    "Item",
                    options=item_options,
                    help="Only items currently in inventory are listed.",
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
        edited_df = edited_df.copy()
        edited_df["item"] = edited_df["item"].apply(
            lambda x: x[0] if isinstance(x, list) and x else (None if isinstance(x, list) else x)
        )

        errors = []
        if edited_df.empty:
            errors.append("Add at least one item to save sale.")
        if (edited_df["quantity"] <= 0).any():
            errors.append("Quantities must be >= 1.")
        if edited_df["item"].isna().any():
            errors.append("Please select an item for every row.")
        if sale_revenue <= 0:
            errors.append("Sale revenue must be greater than 0.")

        if errors:
            for e in errors:
                st.error(e)
            return False

        try:
            item_ids = []
            for _, row in edited_df.iterrows():
                label = str(row["item"]).strip()
                if label not in label_to_id:
                    raise ValueError(f"Item '{label}' not found in inventory.")
                item_ids.append(label_to_id[label])

            edited_df["item_id"] = item_ids
            items_rows = [
                {"item_id": int(r["item_id"]), "quantity": int(r["quantity"])}
                for _, r in edited_df.iterrows()
            ]

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
                [{"item": None, "quantity": 1}]
            )
            return True

        except psycopg2.errors.DatabaseError as e:
            st.error(f"Database error: {e}")
            return False
        except Exception as e:
            st.error(f"Failed to save sale: {e}")
            return False
