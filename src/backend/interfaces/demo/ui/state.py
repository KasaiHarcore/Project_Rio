"""Session state initialization."""

from __future__ import annotations

import os
from datetime import datetime
import streamlit as st
from backend.infrastructure.integrations.llm import form


def init_session_state() -> None:
    defaults = {
        "messages": [],
        "chat_mode": "rag",
        "chat_history": [],
        "current_chat_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "current_thread_id": None,
        "retrieval_k": 5,
        "selected_model": form.get_all_model_names()[0] if form.get_all_model_names() else None,
        "show_settings": False,
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "cohere_api_key": os.getenv("COHERE_API_KEY", ""),
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
