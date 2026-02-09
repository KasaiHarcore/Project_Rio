"""Main chat UI rendering."""

from __future__ import annotations

from uuid import UUID, uuid4

import streamlit as st

from application.services.chat_history_service import chat_history_service
from application.services.agent_service import AgentService
from core.settings import AgentConfig
from utils.log import log_warning
from interfaces.demo.ui.helpers import append_assistant_message, ensure_thread_id, log_message, render_profile_form


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
                thinking_box = st.empty()
                buffer = ""
                st.session_state.stream_buffer = ""
                st.session_state.active_stream_id = uuid4().hex
                final_state = None
                run_id = None
                user_logged = False
                planning_text = ""
                supervisor_reasoning = ""

                def _render_thinking() -> None:
                    if not (planning_text or supervisor_reasoning):
                        return
                    with thinking_box.container():
                        with st.expander("Thinking Process", expanded=False):
                            parts = []
                            if planning_text:
                                parts.append(f"**Planning:**\n{planning_text}")
                            if supervisor_reasoning:
                                parts.append(f"**Supervisor:**\n{supervisor_reasoning}")
                            content = "\n\n".join([p for p in parts if p])
                            st.text_area(
                                "Thinking Process Output",
                                value=content,
                                height=90,
                                disabled=True,
                                label_visibility="collapsed",
                            )

                with st.spinner("Working on your query... 🚀"):
                    stream_id = st.session_state.active_stream_id
                    # LangGraph checkpointing maps checkpoints to SQL threads, so
                    # we must have a stable thread_id before starting the workflow.
                    thread_id = st.session_state.get("current_thread_id") or ensure_thread_id()
                    # Get user_id for memory system
                    current_user_id = None
                    if st.session_state.get("current_user"):
                        current_user_id = st.session_state.current_user.get("id")
                    stream_iter = AgentService.stream_query(
                        prompt,
                        config,
                        history=history,
                        thread_id=thread_id,
                        user_id=current_user_id,
                    )
                    for event in stream_iter:
                        if st.session_state.active_stream_id != stream_id:
                            break
                        etype = event.get("type")
                        if etype == "run_started":
                            run_id = event.get("run_id")
                            # Keep session state in sync in case thread_id was just created.
                            if event.get("thread_id") and not st.session_state.get("current_thread_id"):
                                st.session_state.current_thread_id = event.get("thread_id")
                            if run_id and not user_logged:
                                log_message("user", prompt, run_id=run_id)
                                user_logged = True
                        elif etype == "planning":
                            planning_text = event.get("content", "") or ""
                            _render_thinking()
                        elif etype == "supervisor":
                            # Capture supervisor's reasoning when evaluating worker results
                            decision = event.get("decision") or {}
                            reasoning = decision.get("reasoning", "")
                            if reasoning and event.get("iteration", 0) > 0:
                                # Only show reasoning after first iteration (when evaluating results)
                                supervisor_reasoning = reasoning
                                _render_thinking()
                        elif etype == "token":
                            thinking_box.empty()
                            buffer += event.get("content", "")
                            st.session_state.stream_buffer = buffer
                            placeholder.markdown(buffer + "▌")
                        elif etype == "final":
                            thinking_box.empty()
                            final_state = event.get("result") or {}
                            run_id = event.get("run_id")
                        elif etype == "error":
                            raise RuntimeError(event.get("error") or "Streaming failed")

                answer = (final_state or {}).get("answer") or buffer.strip()
                stats = (final_state or {}).get("stats") or {}
                if run_id and "run_id" not in stats:
                    stats["run_id"] = run_id

                placeholder.markdown(answer or "No response")
                st.session_state.stream_buffer = ""
                st.session_state.active_stream_id = None
                if not user_logged:
                    log_message("user", prompt, run_id=run_id)
                if answer:
                    append_assistant_message(answer, stats=stats or None, run_id=stats.get("run_id"))
            except Exception as e:
                st.session_state.stream_buffer = ""
                st.session_state.active_stream_id = None
                st.error(f"Error: {str(e)}")
