"""Streamlit app entry point (modular)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parents[3]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from infrastructure.integrations.tools.qdrant_tool import vector_db_tool
from infrastructure.integrations.llm.registry import register_all_models
from infrastructure.integrations.llm import form
from application.services.admin_service import AdminService
from utils.log import configure_logging_from_env
from interfaces.demo.components.auth_page import render_auth_routing
from interfaces.demo.ui.state import init_session_state
from interfaces.demo.ui.styles import setup_page, apply_styles
from interfaces.demo.ui.sidebar import render_sidebar
from interfaces.demo.ui.chat import render_chat_interface

load_dotenv()
configure_logging_from_env()

if "models_registered" not in st.session_state:
    register_all_models()
    st.session_state.models_registered = True


def main() -> None:
    setup_page()
    apply_styles()
    init_session_state()

    # Authentication check - renders login/register pages if not authenticated
    is_authenticated = render_auth_routing()

    if is_authenticated:
        render_sidebar()
        render_chat_interface()
        if st.session_state.show_settings:
            with st.expander("Advanced Settings", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Storage Settings**")
                    st.code(f"Path: {vector_db_tool.persist_dir}")
                    st.code(f"Collection: {vector_db_tool.collection_name}")
                with col2:
                    st.markdown("**Model Settings**")
                    st.code(f"Embedding: {vector_db_tool.model_name}")
                    if form.SELECTED_MODEL:
                        st.code(f"LLM: {form.SELECTED_MODEL.name}")

                    # Show current user info
                    if st.session_state.get("current_user"):
                        user = st.session_state.current_user
                        st.markdown("**Current User**")
                        st.code(f"ID: {user['id']}")
                        st.code(f"Joined: {user['created_at'][:10]}")

                # Admin-only Danger Zone
                if st.session_state.get("current_user", {}).get("role") == "admin":
                    st.markdown("---")
                    st.markdown("**Danger Zone**")
                    if st.button(
                        "Reset System Database",
                        type="secondary",
                        use_container_width=True,
                        help="This will delete ALL data (history, users, vector store)",
                    ):
                        try:
                            with st.spinner("Resetting database..."):
                                AdminService.reset_database()

                            # Clear session state
                            st.session_state.messages = []
                            st.session_state.chat_history = []
                            st.session_state.current_thread_id = None

                            st.success("System reset complete. Please refresh.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Reset failed: {e}")


if __name__ == "__main__":
    main()
