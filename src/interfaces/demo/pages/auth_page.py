"""Redirecting auth page for Streamlit multipage UI."""

import streamlit as st
from interfaces.demo.components.auth_page import render_auth_routing


if render_auth_routing():
    st.success("Authenticated. Returning to the main app...")
    try:
        st.switch_page("chat_main.py")
    except Exception:
        st.info("Please select the main app from the sidebar.")
