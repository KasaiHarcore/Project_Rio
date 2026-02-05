"""Shared helper functions for the Streamlit UI."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import streamlit as st

from backend.core.settings import AgentConfig
from backend.infrastructure.dto.models.message import MessageRole
from backend.infrastructure.dto.models.user_profile import UserProfile
from backend.infrastructure.dto.session import get_session
from backend.infrastructure.dto.schemas.user import UserProfileUpdate
from backend.application.services.agent_service import AgentService
from backend.application.services.chat_history_service import chat_history_service
from backend.utils.log import log_warning


def ask_question(question: str, k: int = 5, mode: str = "rag", history: Optional[list] = None):
    user_role = "user"
    if st.session_state.get("current_user"):
        user_role = st.session_state.current_user.get("role", "user")
    thread_id = ensure_thread_id()
    config = AgentConfig(
        mode=mode,
        user_role=user_role,
        top_k=k,
        model_name=st.session_state.selected_model,
    )

    return AgentService.execute_query(
        question,
        config,
        history=history,
        thread_id=thread_id,
    )


def append_assistant_message(content: str, *, stats: Optional[dict] = None, run_id: Optional[str] = None) -> None:
    payload = {"role": "assistant", "content": content}
    if stats is not None:
        payload["stats"] = stats
    st.session_state.messages.append(payload)
    log_message("assistant", content, run_id=run_id)


def load_user_profile(user_id: UUID) -> dict:
    try:
        with get_session() as session:
            profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                return {}
            return {
                "full_name": profile.full_name or "",
                "phone": profile.phone or "",
                "address": profile.address or "",
                "company": profile.company or "",
                "job_title": profile.job_title or "",
                "locale": profile.locale or "",
            }
    except Exception as e:
        log_warning(f"Failed to load user profile: {e}")
        return {}


def save_user_profile(user_id: UUID, data: dict) -> None:
    with get_session() as session:
        profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if profile:
            for key, value in data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
        else:
            profile = UserProfile(user_id=user_id, **data)
            session.add(profile)
        session.commit()


def render_profile_form(user_id: UUID) -> None:
    profile = load_user_profile(user_id)
    with st.form("user_profile_form", clear_on_submit=False):
        st.caption("Profile information is optional and user-provided only.")
        full_name = st.text_input("Full name", value=profile.get("full_name", ""))
        phone = st.text_input("Phone", value=profile.get("phone", ""))
        address = st.text_input("Address", value=profile.get("address", ""))
        company = st.text_input("Company", value=profile.get("company", ""))
        job_title = st.text_input("Job title", value=profile.get("job_title", ""))
        locale = st.text_input("Locale", value=profile.get("locale", ""))

        submitted = st.form_submit_button("Save Profile")
        if submitted:
            try:
                save_user_profile(
                    user_id,
                    {
                        "full_name": full_name.strip() or None,
                        "phone": phone.strip() or None,
                        "address": address.strip() or None,
                        "company": company.strip() or None,
                        "job_title": job_title.strip() or None,
                        "locale": locale.strip() or None,
                    },
                )
                st.success("Profile saved")
            except Exception as e:
                st.error(f"Failed to save profile: {e}")


def ensure_thread_id() -> Optional[str]:
    """Ensure a Thread exists for the current chat and return its ID."""
    if not st.session_state.get("current_user"):
        return None
    if st.session_state.get("current_thread_id"):
        return st.session_state.current_thread_id

    try:
        user_id = UUID(st.session_state.current_user["id"])
        title = f"Chat {st.session_state.current_chat_id}"
        thread_id = chat_history_service.ensure_thread(user_id, st.session_state.current_thread_id, title)
        st.session_state.current_thread_id = thread_id
        return thread_id
    except Exception as e:
        log_warning(f"Failed to create thread: {e}")
        return None


def log_message(role: str, content: str, *, run_id: Optional[str] = None) -> None:
    """Persist a chat message to SQL (best-effort)."""
    thread_id = ensure_thread_id()
    if not thread_id:
        return
    try:
        role_map = {
            "user": MessageRole.USER,
            "assistant": MessageRole.ASSISTANT,
            "tool": MessageRole.TOOL,
        }
        msg_role = role_map.get(role, MessageRole.USER)
        chat_history_service.append_message_async(
            user_id=UUID(st.session_state.current_user["id"]),
            thread_id=thread_id,
            role=msg_role,
            content=content,
            run_id=run_id,
        )
    except Exception as e:
        log_warning(f"Failed to log message: {e}")
