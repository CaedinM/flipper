import streamlit as st
import pandas as pd
from datetime import date
import psycopg2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import run_query_df, insert_order_with_items
from .utils import sanitize_order_num

ERA_OPTIONS = ["Mega Evolution", "Scarlet & Violet"]

def render_new_order_form():
    if "order_line_items" not in st.session_state:
        st.session_state.order_line_items = []

    # ── Order Info ────────────────────────────────────────────────────────────
    st.subheader("Order Info")
    col1, col2 = st.columns(2)
    with col1:
        raw_order_num = st.text_input("Order #", placeholder="e.g., AMZ-12345", key="order_num_input")
        order_date = st.date_input("Order Date", value=date.today(), key="order_date_input")
        seller = st.selectbox(
            "Platform / Retailer",
            options=["Target", "Walmart", "Pokemon Center", "Best Buy", "DICK's Sporting Goods", "LEGO Shop", "Other"],
            key="order_seller_input",
        )
    with col2:
        total_cost = st.number_input(
            "Total Cost", min_value=0.0, max_value=99999999.99, step=0.01,
            help="Total paid including shipping and taxes. Exclude PAS fees.",
            key="order_total_input",
        )
        shipping_cost = st.number_input(
            "Shipping Cost", min_value=0.0, max_value=99999999.99, step=0.01,
            key="order_shipping_input",
        )

    st.divider()

    # ── Item Selector ─────────────────────────────────────────────────────────
    st.subheader("Add Items")

    sel1, sel2, sel3 = st.columns(3)
    with sel1:
        selected_era = st.selectbox("Era", ERA_OPTIONS, key="order_era_select")

    sets_df = run_query_df(
        "SELECT DISTINCT set FROM items WHERE era = %s AND set IS NOT NULL ORDER BY set",
        0, (selected_era,)
    )
    set_options = sets_df["set"].tolist() if not sets_df.empty else []

    with sel2:
        # Key includes era so the widget resets when era changes
        selected_set = st.selectbox("Set", set_options, key=f"order_set_select_{selected_era}")

    products_df = run_query_df(
        "SELECT item_id, product FROM items WHERE era = %s AND set = %s AND product IS NOT NULL ORDER BY product",
        0, (selected_era, selected_set),
    ) if selected_set else pd.DataFrame(columns=["item_id", "product"])
    product_options = products_df["product"].tolist()
    product_to_id = dict(zip(products_df["product"], products_df["item_id"]))

    with sel3:
        # Key includes era+set so the widget resets when set changes
        selected_product = st.selectbox("Product", product_options, key=f"order_product_select_{selected_era}_{selected_set}")

    qty_col, price_col, pas_col, btn_col = st.columns([1, 1, 1, 1])
    with qty_col:
        item_qty = st.number_input("Quantity", min_value=1, step=1, value=1, key="order_item_qty")
    with price_col:
        item_price = st.number_input("Price Tag ($)", min_value=0.0, step=0.01, value=0.0, key="order_item_price")
    with pas_col:
        item_pas = st.number_input("PAS Fee / Item ($)", min_value=0.0, step=0.01, value=0.0, key="order_item_pas")
    with btn_col:
        st.write("")
        st.write("")
        if st.button("＋ Add Item", use_container_width=True, key="add_item_btn"):
            if not selected_product:
                st.error("Select a product before adding.")
            else:
                st.session_state.order_line_items.append({
                    "item_id": int(product_to_id[selected_product]),
                    "era": selected_era,
                    "set": selected_set,
                    "product": selected_product,
                    "quantity": int(item_qty),
                    "pricetag": float(item_price),
                    "pas_fee_per_item": float(item_pas),
                })
                st.rerun()

    # ── Line Items List ───────────────────────────────────────────────────────
    if st.session_state.order_line_items:
        st.divider()
        st.subheader("Order Items")

        header = st.columns([2, 2, 3, 1, 1, 1, 0.4])
        for col, label in zip(header, ["Era", "Set", "Product", "Qty", "Price", "PAS", ""]):
            col.markdown(f"**{label}**")

        to_remove = None
        for i, item in enumerate(st.session_state.order_line_items):
            cols = st.columns([2, 2, 3, 1, 1, 1, 0.4])
            cols[0].write(item["era"])
            cols[1].write(item["set"])
            cols[2].write(item["product"])
            cols[3].write(str(item["quantity"]))
            cols[4].write(f"${item['pricetag']:.2f}")
            cols[5].write(f"${item['pas_fee_per_item']:.2f}")
            if cols[6].button("✕", key=f"remove_item_{i}"):
                to_remove = i

        if to_remove is not None:
            st.session_state.order_line_items.pop(to_remove)
            st.rerun()

    # ── Actions ───────────────────────────────────────────────────────────────
    st.divider()
    col_cancel, col_save = st.columns(2)
    with col_cancel:
        if st.button("Cancel", use_container_width=True, key="order_cancel_btn"):
            st.session_state.order_line_items = []
            st.session_state.show_new_order = False
            st.rerun()
    with col_save:
        if st.button("Save Order", type="primary", use_container_width=True, key="order_save_btn"):
            order_num = sanitize_order_num(raw_order_num)
            errors = []
            if not order_num.strip():
                errors.append("Order # is required.")
            if not st.session_state.order_line_items:
                errors.append("Add at least one item.")
            if errors:
                for e in errors:
                    st.error(e)
                return False
            try:
                insert_order_with_items(
                    order_data={
                        "order_num": order_num.strip(),
                        "order_date": order_date,
                        "seller": seller,
                        "total_cost": total_cost,
                        "shipping_cost": shipping_cost,
                        "tax_rate": 0.0975,
                    },
                    items_rows=[
                        {
                            "item_id": r["item_id"],
                            "quantity": r["quantity"],
                            "pricetag": r["pricetag"],
                            "pas_fee_per_item": r["pas_fee_per_item"],
                        }
                        for r in st.session_state.order_line_items
                    ],
                )
                st.session_state.order_line_items = []
                return True
            except psycopg2.errors.UniqueViolation:
                st.error("That Order # already exists.")
                return False
            except Exception as e:
                st.error(f"Failed to save order: {e}")
                return False

    return False
