import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.db import create_calculate_cost_basis_trigger

def init_state():
    st.session_state.setdefault("refresh_token", 0)
    if "triggers_applied" not in st.session_state:
        create_calculate_cost_basis_trigger()
        st.session_state["triggers_applied"] = True