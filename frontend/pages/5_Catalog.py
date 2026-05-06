import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.db import run_query_df, upsert_item
from frontend.components.theme import inject_theme
from frontend.state import init_state

if "refresh_token" not in st.session_state:
    init_state()

st.set_page_config(page_title="Catalog", page_icon="🦭", layout="wide")

ERA_OPTIONS = ["Mega Evolution", "Scarlet & Violet"]

def render_catalog():
    inject_theme()
    st.header("Product Catalog")

    tab_me, tab_sv = st.tabs(["Mega Evolution", "Scarlet & Violet"])

    for tab, era in [(tab_me, "Mega Evolution"), (tab_sv, "Scarlet & Violet")]:
        with tab:
            sets_df = run_query_df(
                "SELECT DISTINCT set FROM items WHERE era = %s AND set IS NOT NULL ORDER BY set",
                st.session_state["refresh_token"], (era,)
            )
            if sets_df.empty:
                st.info("No sets in catalog yet.")
            else:
                for set_name in sets_df["set"].tolist():
                    products_df = run_query_df(
                        "SELECT product FROM items WHERE era = %s AND set = %s AND product IS NOT NULL ORDER BY product",
                        st.session_state["refresh_token"], (era, set_name)
                    )
                    products = products_df["product"].tolist()
                    with st.expander(f"**{set_name}** — {len(products)} product(s)", expanded=False):
                        for p in products:
                            st.write(f"• {p}")

    st.divider()
    st.subheader("Add Product")

    col1, col2, col3, col4 = st.columns([1, 2, 3, 1])
    with col1:
        new_era = st.selectbox("Era", ERA_OPTIONS, key="catalog_era_select")

    sets_df = run_query_df(
        "SELECT DISTINCT set FROM items WHERE era = %s AND set IS NOT NULL ORDER BY set",
        0, (new_era,)
    )
    existing_sets = sets_df["set"].tolist() if not sets_df.empty else []

    with col2:
        set_choice = st.selectbox(
            "Set",
            options=existing_sets + ["— New set —"],
            key=f"catalog_set_select_{new_era}",
        )
        if set_choice == "— New set —":
            new_set = st.text_input("New set name", key="catalog_new_set_input")
        else:
            new_set = set_choice

    with col3:
        new_product = st.text_input("Product name", placeholder="e.g. Charizard ex Special Collection", key="catalog_product_input")

    with col4:
        st.write("")
        st.write("")
        if st.button("Add", type="primary", use_container_width=True, key="catalog_add_btn"):
            if not new_set or not new_set.strip():
                st.error("Set name is required.")
            elif not new_product or not new_product.strip():
                st.error("Product name is required.")
            else:
                try:
                    upsert_item(
                        category="Pokemon",
                        era=new_era,
                        set=new_set.strip(),
                        product=new_product.strip(),
                    )
                    st.success(f"Added: {new_era} · {new_set.strip()} · {new_product.strip()}")
                    st.session_state.refresh_token += 1
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add product: {e}")

render_catalog()
