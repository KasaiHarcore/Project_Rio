"""Sidebar UI rendering."""

from __future__ import annotations

import os
import time
import tempfile
from pathlib import Path
from uuid import UUID

import streamlit as st

from dotenv import set_key, find_dotenv
from backend.infrastructure.integrations.tools.qdrant_tool import vector_db_tool
from backend.infrastructure.integrations.llm import form
from backend.application.services.auth_service import AuthService
from backend.infrastructure.dto.session import get_session
from backend.application.services.chat_history_service import chat_history_service
from backend.utils.log import log_warning


def render_sidebar() -> None:
    with st.sidebar:
        # User info at top
        if st.session_state.get("current_user"):
            user = st.session_state.current_user
            st.markdown(f"### 👤 {user['username']}")
            st.caption(f"Role: {user['role'].upper()}")
            if st.button("Edit Profile", type="secondary", use_container_width=True):
                st.session_state.show_profile_dialog = True
            st.markdown("---")

        if st.button("New Chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.current_chat_id = time.strftime("%Y%m%d_%H%M%S")
            st.session_state.current_thread_id = None
            st.rerun()

        st.markdown("---")

        # Settings Menu (Mode/Uploads)
        st.markdown("**Chat Mode**")
        is_admin = (
            st.session_state.get("current_user")
            and st.session_state.current_user.get("role") == "admin"
        )
        if not is_admin and st.session_state.chat_mode == "sql":
            st.session_state.chat_mode = "rag"
        mode_map = {"Auto": "chat", "RAG": "rag", "Web Search": "web"}
        if is_admin:
            mode_map["SQL"] = "sql"
        reverse_map = {v: k for k, v in mode_map.items()}
        display_modes = list(mode_map.keys())
        current_display = reverse_map.get(st.session_state.chat_mode, "RAG")
        selected_display = st.selectbox(
            "Select Mode",
            options=display_modes,
            index=display_modes.index(current_display),
            label_visibility="collapsed",
            key="sidebar_mode_select",
        )
        new_mode = mode_map[selected_display]
        if new_mode != st.session_state.chat_mode:
            st.session_state.chat_mode = new_mode
            st.rerun()

        if st.session_state.chat_mode in {"rag", "chat"}:
            with st.expander("Upload Documents"):
                uploaded_files = st.file_uploader(
                    "Add to knowledge base",
                    type=["txt", "md", "pdf", "json", "csv", "html", "htm", "docx"],
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                )
                if uploaded_files and st.button("Upload Files", use_container_width=True):
                    for uploaded_file in uploaded_files:
                        if getattr(uploaded_file, "size", 0) == 0:
                            st.warning(f"{uploaded_file.name} is empty. Skipped.")
                            continue
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            tmp_file_path = tmp_file.name

                        try:
                            vector_db_tool.ingest_file(tmp_file_path)
                            st.success(f"{uploaded_file.name} uploaded")
                        except Exception as e:
                            st.error(f"{uploaded_file.name} failed: {e}")
                        finally:
                            if tmp_file_path and os.path.exists(tmp_file_path):
                                os.unlink(tmp_file_path)

        st.markdown("---")

        with st.expander("Overall Status", expanded=False):
            try:
                info = vector_db_tool.get_collection_info()
                st.metric("Vector Count", info.get("vectors_count", "N/A"))
                st.metric("Collection", info["collection_name"])
                st.caption(f"**Model:** {form.SELECTED_MODEL.name if form.SELECTED_MODEL else 'Not initialized'}")
            except Exception as e:
                st.warning(f"Status unavailable: {str(e)}")

        st.markdown("**Chat History**")
        search_query = st.text_input("Search chats", placeholder="Search...", label_visibility="collapsed")
        if st.session_state.get("current_user"):
            try:
                threads = chat_history_service.list_threads(UUID(st.session_state.current_user["id"]), limit=20)
                st.session_state.chat_history = [
                    {"id": str(t.id), "title": t.title or "Untitled", "updated_at": t.updated_at}
                    for t in threads
                ]
            except Exception as e:
                log_warning(f"Failed to load chat history: {e}")

        if st.session_state.chat_history:
            for chat in st.session_state.chat_history[-10:]:
                title = chat["title"] or "Untitled"
                if search_query and search_query.lower() not in title.lower():
                    continue

                col1, col2 = st.columns([0.70, 0.30])
                with col1:
                    if st.button(f"{title[:20]}...", key=f"chat_{chat['id']}", use_container_width=True):
                        st.session_state.current_thread_id = chat["id"]
                        try:
                            msgs = chat_history_service.get_messages(UUID(chat["id"]), limit=200)
                            st.session_state.messages = [
                                {"role": m.role.value, "content": m.content}
                                for m in msgs
                            ]
                        except Exception as e:
                            log_warning(f"Failed to load messages: {e}")
                        st.rerun()
                with col2:
                    if is_admin and st.button(
                        "Delete",
                        key=f"del_{chat['id']}",
                        help="Delete chat",
                        use_container_width=True,
                    ):
                        try:
                            cid = UUID(chat["id"])
                            chat_history_service.hard_delete_thread(cid)
                            st.toast("Chat permanently deleted", icon="🗑️")

                            # Clear current thread if it was the one deleted
                            if st.session_state.get("current_thread_id") == chat["id"]:
                                st.session_state.current_thread_id = None
                                st.session_state.messages = []

                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")
        else:
            st.caption("No chat history yet")

        st.markdown("---")

        with st.expander("User Settings", expanded=False):
            st.markdown("**API Keys**")
            openai_key = st.text_input("OpenAI API Key", value=st.session_state.openai_api_key, type="password", placeholder="sk-...")
            if openai_key != st.session_state.openai_api_key:
                st.session_state.openai_api_key = openai_key
                os.environ["OPENAI_API_KEY"] = openai_key
                env_file = find_dotenv()
                if env_file:
                    set_key(env_file, "OPENAI_API_KEY", openai_key)
                    st.success("✓ OpenAI key updated")

            openrouter_key = st.text_input("OpenRouter API Key", value=st.session_state.openrouter_api_key, type="password", placeholder="sk-or-...")
            if openrouter_key != st.session_state.openrouter_api_key:
                st.session_state.openrouter_api_key = openrouter_key
                os.environ["OPENROUTER_API_KEY"] = openrouter_key
                env_file = find_dotenv()
                if env_file:
                    set_key(env_file, "OPENROUTER_API_KEY", openrouter_key)
                    st.success("✓ OpenRouter key updated")

            cohere_key = st.text_input("Cohere API Key", value=st.session_state.cohere_api_key, type="password", placeholder="...")
            if cohere_key != st.session_state.cohere_api_key:
                st.session_state.cohere_api_key = cohere_key
                os.environ["COHERE_API_KEY"] = cohere_key
                env_file = find_dotenv()
                if env_file:
                    set_key(env_file, "COHERE_API_KEY", cohere_key)
                    st.success("✓ Cohere key updated")

            tavily_key = st.text_input("Tavily API Key", value=st.session_state.tavily_api_key, type="password", placeholder="tvly-...")
            if tavily_key != st.session_state.tavily_api_key:
                st.session_state.tavily_api_key = tavily_key
                os.environ["TAVILY_API_KEY"] = tavily_key
                env_file = find_dotenv()
                if env_file:
                    set_key(env_file, "TAVILY_API_KEY", tavily_key)
                    st.success("✓ Tavily key updated")

            st.markdown("---")
            st.markdown("**Model Selection**")
            available_models = form.get_all_model_names()
            if not available_models:
                st.error("No models available. Check your configuration.")
                return
            selected = st.selectbox(
                "Choose LLM",
                options=available_models,
                index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
                label_visibility="collapsed",
            )
            if selected != st.session_state.selected_model:
                st.session_state.selected_model = selected
                form.set_model(selected)
                st.success(f"✓ Switched to {selected}")

            st.markdown("---")
            st.markdown("**Retrieval Settings**")
            st.session_state.retrieval_k = st.slider("Top-K Results", 1, 20, st.session_state.retrieval_k)

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Settings", use_container_width=True):
                st.session_state.show_settings = not st.session_state.show_settings
        with col2:
            if st.button("Logout", use_container_width=True, type="secondary"):
                # Log logout event
                if st.session_state.get("current_user"):
                    try:
                        with get_session() as session:
                            AuthService.logout(session, UUID(st.session_state.current_user["id"]))
                    except Exception:
                        pass  # Silent fail on logout logging

                # Clear session state
                st.session_state.authenticated = False
                st.session_state.current_user = None
                st.session_state.messages = []
                st.success("✅ Logged out successfully")
                st.rerun()
