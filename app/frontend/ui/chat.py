"""Main chat UI rendering."""

from __future__ import annotations

from uuid import UUID

import streamlit as st

from backend.services.chat_history_service import chat_history_service
from backend.services.agent_service import AgentService
from backend.core.settings import AgentConfig
from backend.utils.log import log_warning
from frontend.ui.helpers import append_assistant_message, log_message, render_profile_form


def render_chat_interface() -> None:
    if st.session_state.get("current_user"):
        user_id = UUID(st.session_state.current_user["id"])
        if st.session_state.get("show_profile_dialog"):
            if hasattr(st, "dialog"):
                @st.dialog("Your Profile")
                def _profile_dialog():
                    render_profile_form(user_id)

                _profile_dialog()
            else:
                with st.expander("Your Profile", expanded=True):
                    render_profile_form(user_id)
            st.session_state.show_profile_dialog = False

    # Chat messages container
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "stats" in msg:
                with st.expander("Stats"):
                    s = msg["stats"]
                    st.metric("Tokens", s["total_tokens"])
                    st.caption(f"Cost: ${s['total_cost']:.6f}")

    # Input
    prompt = st.chat_input(f"Message FPT Policy Agent ({st.session_state.chat_mode.upper()} mode)...")

    # Process user input
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        log_message("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        history = []
        if st.session_state.get("current_thread_id"):
            try:
                history = chat_history_service.get_memory_buffer(UUID(st.session_state.current_thread_id))
            except Exception as e:
                log_warning(f"Failed to load memory buffer: {e}")

        with st.chat_message("assistant"):
            try:
                user_role = "user"
                if st.session_state.get("current_user"):
                    user_role = st.session_state.current_user.get("role", "user")

                config = AgentConfig(
                    mode=st.session_state.chat_mode,
                    user_role=user_role,
                    top_k=st.session_state.retrieval_k,
                    model_name=st.session_state.selected_model,
                )

                placeholder = st.empty()
                buffer = ""
                final_state = None
                run_id = None

                with st.spinner("Working on your query... 🚀"):
                    for event in AgentService.stream_query(
                        prompt,
                        config,
                        history=history,
                        thread_id=st.session_state.get("current_thread_id"),
                    ):
                        etype = event.get("type")
                        if etype == "token":
                            buffer += event.get("content", "")
                            placeholder.markdown(buffer + "▌")
                        elif etype == "final":
                            final_state = event.get("result") or {}
                            run_id = event.get("run_id")
                        elif etype == "error":
                            raise RuntimeError(event.get("error") or "Streaming failed")

                answer = (final_state or {}).get("answer") or buffer.strip()
                stats = (final_state or {}).get("stats") or {}
                if run_id and "run_id" not in stats:
                    stats["run_id"] = run_id

                placeholder.markdown(answer or "No response")
                if answer:
                    append_assistant_message(answer, stats=stats or None, run_id=stats.get("run_id"))
            except Exception as e:
                st.error(f"Error: {str(e)}")
