import streamlit as st
import datetime as dt
import psycopg2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import insert_expense


def render_add_expense_form():
    """
    Form component to manually add a new other expense.
    Returns True if saved successfully, False otherwise.
    """
    with st.form("add_expense_form", clear_on_submit=True):
        st.subheader("New Expense")

        col_date, col_cost = st.columns(2)
        with col_date:
            expense_date = st.date_input(
                "Date",
                value=dt.date.today(),
                key="expense_date_input",
            )
        with col_cost:
            expense_cost = st.number_input(
                "Amount ($)",
                step=0.01,
                format="%.2f",
                key="expense_cost_input",
                help="Use a negative value to record money recouped (e.g. selling off supplies)",
            )

        description = st.text_input(
            "Description",
            placeholder="e.g. Packing tape, Walmart+ subscription, Shipping boxes…",
            key="expense_description_input",
        )

        col_cancel, col_save = st.columns(2)
        with col_cancel:
            cancelled = st.form_submit_button("Cancel", type="secondary", width="stretch")
        with col_save:
            submitted = st.form_submit_button("Add Expense", type="primary", width="stretch")

        if cancelled:
            return "cancelled"

        if submitted:
            errors = []
            if not description.strip():
                errors.append("Description is required.")
            if expense_cost == 0:
                errors.append("Amount cannot be $0.00.")

            if errors:
                for e in errors:
                    st.error(e)
                return False

            try:
                insert_expense(expense_date, description, expense_cost)
                return True
            except psycopg2.Error as e:
                st.error(f"Database error: {e}")
                return False
            except Exception as e:
                st.error(f"Failed to add expense: {e}")
                return False

    return False
