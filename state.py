import streamlit as st

def init_state():
    st.session_state.setdefault("refresh_token", 0)