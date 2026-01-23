"""
Streamlit Web Interface for FPT Policy RAG Agent
"""

import streamlit as st
import sys
import time
from pathlib import Path
from datetime import datetime
import tempfile
import os
from uuid import UUID
from typing import Optional

# Add app directory for imports
APP_DIR = Path(__file__).parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv, set_key, find_dotenv
from backend.services.tools.qdrant_tool import vector_db_tool
from backend.services.agent_service import AgentService
from backend.services.llm.registry import register_all_models
from backend.services.llm import form
from backend.core.settings import AgentConfig
from backend.utils.log import log_info, log_success, log_error, log_warning, configure_logging_from_env
from frontend.components.auth_page import render_auth_routing
from backend.services.auth_service import AuthService
from backend.services.admin_service import AdminService
from backend.db.session import get_session
from backend.db.repositories.user_profile_repo import UserProfileRepository
from backend.schemas.user import UserProfileUpdate
from backend.db.models.thread import Thread, ThreadStatus
from backend.db.models.message import Message, MessageRole
from backend.services.chat_history_service import chat_history_service

# Load environment
load_dotenv()
configure_logging_from_env()

# Register models once
if "models_registered" not in st.session_state:
    register_all_models()
    st.session_state.models_registered = True


# Initialize session state with defaults
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
    "pending_approval": None,
    "pending_approval_thread_id": None,
    "pending_approval_run_id": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Page config for a sleek look
st.set_page_config(
    page_title="FPT Policy RAG Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS: Dark theme like Grok, with muted red edges. Added !important to key overrides for reliability based on screenshot (e.g., sidebar blue -> dark, input dark, buttons red-accented).
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* CSS Variables for theme consistency */
    :root {
        --bg-dark: #121212; /* Soft black for less eye strain */
        --bg-darker: #0A0A0A; /* Deeper black for gradients/layers */
        --bg-light: #1E1E1E; /* Subtle gray for cards/expanders */
        --text-primary: #EDEDED; /* Off-white for readability */
        --text-secondary: #A9A9A9; /* Muted gray for secondary text */
        --accent-white: #FFFFFF; /* White for edges */
        --border-white: 1px solid var(--accent-white); /* White edges as requested */
        --shadow-soft: 0 2px 8px rgba(0, 0, 0, 0.3); /* Subtle shadows for depth */
        --font-main: 'Inter', sans-serif;
        --font-code: 'JetBrains Mono', monospace;
    }

    /* Hide Streamlit defaults */
    #MainMenu, footer, header { visibility: hidden; }

    /* Global styles */
    html, body, [class*="css"]  { font-family: var(--font-main); color: var(--text-primary) !important; }
    .stApp { background: linear-gradient(135deg, var(--bg-darker) 0%, var(--bg-dark) 50%, #1A1A1A 100%) !important; }
    
    /* Button overrides */
    .stButton > button { border: none !important; }
    [data-testid="stSidebar"] .stButton > button { border: var(--border-white) !important; }

    /* Typography */
    h1, h2, h3, h4, h5, h6 { color: var(--text-primary) !important; }
    p, div, span, label { color: var(--text-primary) !important; }
    .caption, small { color: var(--text-secondary) !important; }
    strong, b { color: #FFFFFF !important; font-weight: 600; }

    /* Chat messages */
    .stChatMessage { margin: 1rem 0; background: transparent !important; }
    .stChatMessage[data-testid="user-message"] > div {
        background: var(--bg-light) !important;
        border-radius: 18px 18px 4px 18px;
        padding: 1rem 1.25rem;
        box-shadow: var(--shadow-soft);
        max-width: 75%;
        border: var(--border-white); /* White edge */
        color: var(--text-primary) !important;
    }
    .stChatMessage[data-testid="assistant-message"] > div {
        background: var(--bg-light) !important;
        border-radius: 18px 18px 18px 4px;
        padding: 1rem 1.25rem;
        box-shadow: var(--shadow-soft);
        max-width: 85%;
        border: var(--border-white); /* White edge */
        color: var(--text-primary) !important;
    }
    .stChatMessage p { line-height: 1.8; margin-bottom: 0.75rem; color: var(--text-primary) !important; }
    .stChatMessage ul, .stChatMessage ol { margin-left: 1.5rem; margin-bottom: 1rem; color: var(--text-primary) !important; }
    .stChatMessage li { margin-bottom: 0.5rem; line-height: 1.7; color: var(--text-primary) !important; }
    .stChatMessage blockquote {
        border-left: 4px solid var(--accent-white);
        padding: 0.5rem 1rem;
        margin: 1rem 0;
        background: rgba(255, 255, 255, 0.1); /* Subtle white tint */
        border-radius: 0 8px 8px 0;
        color: var(--text-secondary) !important;
        font-style: italic;
    }

    /* Code and tables */
    code { background: var(--bg-darker) !important; padding: 0.2rem 0.5rem; border-radius: 4px; font-family: var(--font-code); color: #FF6347 !important; border: var(--border-white); }
    pre { background: var(--bg-darker) !important; border: var(--border-white); border-radius: 8px; padding: 1rem; overflow-x: auto; margin: 1rem 0; }
    pre code { background: transparent !important; padding: 0; border: none; font-size: 0.9rem; color: var(--text-primary) !important; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; background: var(--bg-light) !important; border: var(--border-white); }
    th { background: var(--bg-darker) !important; color: var(--text-primary) !important; padding: 0.75rem; text-align: left; border: var(--border-white); }
    td { border: var(--border-white); padding: 0.75rem; color: var(--text-primary) !important; }
    tr:nth-child(even) { background: #282828 !important; }

    /* Input and buttons - White accents */
    .stChatInputContainer { 
        background: var(--bg-darker) !important; 
        border-radius: 8px; 
        box-shadow: var(--shadow-soft); 
        padding: 0.5rem 1rem; 
        border: var(--border-white);
    }
    .stChatInputContainer:focus-within { border-color: var(--accent-white) !important; box-shadow: 0 4px 24px rgba(255, 255, 255, 0.1); }
    .stChatInputContainer input { color: var(--text-primary) !important; background: transparent !important; }
    .stChatInputContainer input::placeholder { color: var(--text-secondary) !important; }

    /* Sidebar and expanders - Force dark override */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, var(--bg-dark) 0%, var(--bg-light) 100%) !important; border-right: var(--border-white); }
    [data-testid="stSidebar"] * { color: var(--text-primary) !important; }
    [data-testid="stSidebarCollapseButton"] { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    .streamlit-expanderHeader { background: var(--bg-light) !important; border-radius: 8px; font-weight: 500; color: var(--text-primary) !important; border: var(--border-white); }
    .streamlit-expanderHeader:hover { background: #282828 !important; }
    .streamlit-expanderContent { border: var(--border-white); border-top: none; background: var(--bg-dark) !important; color: var(--text-primary) !important; }

    /* Popover, selectboxes, text inputs, etc. */
    [data-testid="stPopover"] { background: var(--bg-light) !important; border-radius: 12px; box-shadow: var(--shadow-soft); border: var(--border-white); color: var(--text-primary) !important; }
    .stSelectbox > div > div, .stTextInput > div > div > input { color: var(--text-primary) !important; background: var(--bg-darker) !important; border: var(--border-white); }
    .stFileUploader { background: var(--bg-light) !important; border: 2px dashed var(--text-secondary) !important; border-radius: 8px; }
    [data-testid="stMetric"] { background: var(--bg-light) !important; padding: 1rem; border-radius: 8px; border: var(--border-white); }
    [data-testid="stMetricLabel"] { color: var(--text-secondary) !important; font-weight: 500; }
    [data-testid="stMetricValue"] { color: var(--text-primary) !important; font-weight: 700; }
</style>
""",
    unsafe_allow_html=True,
)


# Helper: Process question through agent
def ask_question(question: str, k: int = 5, mode: str = "rag", history: Optional[list] = None):
    user_role = "user"
    if st.session_state.get("current_user"):
        user_role = st.session_state.current_user.get("role", "user")
    thread_id = _ensure_thread_id()
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


def _load_user_profile(user_id: UUID) -> dict:
    try:
        with get_session() as session:
            repo = UserProfileRepository(session)
            profile = repo.get_by_user_id(user_id)
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


def _save_user_profile(user_id: UUID, data: dict) -> None:
    with get_session() as session:
        repo = UserProfileRepository(session)
        repo.upsert(user_id, UserProfileUpdate(**data))


def _render_profile_form(user_id: UUID) -> None:
    profile = _load_user_profile(user_id)
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
                _save_user_profile(
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


def _ensure_thread_id() -> Optional[str]:
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


def _log_message(role: str, content: str, *, run_id: Optional[str] = None) -> None:
    """Persist a chat message to SQL (best-effort)."""
    thread_id = _ensure_thread_id()
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


# UI: Sidebar
def render_sidebar():
    with st.sidebar:
        # User info at top
        if st.session_state.get("current_user"):
            user = st.session_state.current_user
            st.markdown(f"### 👤 {user['username']}")
            st.caption(f"Role: {user['role'].upper()}")
            if st.button("Edit Profile", type="secondary", use_container_width=True):
                st.session_state.show_profile_dialog = True
            st.markdown("---")
        
        st.markdown("### FPT Policy Agent")
        st.markdown("---")

        if st.button("New Chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.current_thread_id = None
            st.rerun()

        st.markdown("---")
        
        # Moved Settings Menu (Mode/Uploads) here for better layout
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
            key="sidebar_mode_select"
        )
        new_mode = mode_map[selected_display]
        if new_mode != st.session_state.chat_mode:
            st.session_state.chat_mode = new_mode
            st.rerun()

        if st.session_state.chat_mode == "rag" or st.session_state.chat_mode == "chat":
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


# UI: Main chat
def render_chat_interface():
    if st.session_state.get("current_user"):
        user_id = UUID(st.session_state.current_user["id"])
        if st.session_state.get("show_profile_dialog"):
            if hasattr(st, "dialog"):
                @st.dialog("Your Profile")
                def _profile_dialog():
                    _render_profile_form(user_id)

                _profile_dialog()
            else:
                with st.expander("Your Profile", expanded=True):
                    _render_profile_form(user_id)
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

    if st.session_state.pending_approval:
        with st.expander("SQL Approval Required", expanded=True):
            approval = st.session_state.pending_approval
            st.markdown("A SQL action requires your approval before execution.")
            if isinstance(approval, dict):
                st.markdown("**Proposed SQL:**")
                st.code(approval.get("query", ""), language="sql")
                params = approval.get("params") or {}
                if params:
                    st.markdown("**Parameters:**")
                    st.json(params)
            col1, col2 = st.columns(2)
            approve = col1.button("Approve", type="primary", use_container_width=True)
            reject = col2.button("Reject", type="secondary", use_container_width=True)

            if approve or reject:
                thread_id = st.session_state.pending_approval_thread_id or st.session_state.get("current_thread_id")
                if not thread_id:
                    st.error("No thread ID available to resume workflow.")
                else:
                    try:
                        result = AgentService.resume_query(thread_id=thread_id, approved=approve)
                        st.session_state.pending_approval = None
                        st.session_state.pending_approval_thread_id = None
                        st.session_state.pending_approval_run_id = None

                        if result.get("status") == "approval_required":
                            st.session_state.pending_approval = result.get("interrupt")
                            st.session_state.pending_approval_thread_id = result.get("thread_id") or thread_id
                            st.session_state.pending_approval_run_id = result.get("run_id")
                            st.rerun()
                        else:
                            answer = result.get("answer", "")
                            stats = result.get("stats", {})
                            if answer:
                                with st.chat_message("assistant"):
                                    st.markdown(answer)
                                st.session_state.messages.append({"role": "assistant", "content": answer, "stats": stats})
                                _log_message("assistant", answer, run_id=stats.get("run_id"))
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to resume workflow: {e}")

    # Standard Streamlit chat input (automatically pinned to bottom)
    prompt = None
    if not st.session_state.pending_approval:
        prompt = st.chat_input(f"Message FPT Policy Agent ({st.session_state.chat_mode.upper()} mode)...")
    else:
        st.info("Pending approval. Please approve or reject the SQL action above to continue.")
    
    # Process user input
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        _log_message("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Working on your query... 🚀"):  # Grok-like fun spinner
                try:
                    history = []
                    if st.session_state.get("current_thread_id"):
                        try:
                            history = chat_history_service.get_memory_buffer(
                                UUID(st.session_state.current_thread_id)
                            )
                        except Exception as e:
                            log_warning(f"Failed to load memory buffer: {e}")
                    result = ask_question(
                        prompt,
                        k=st.session_state.retrieval_k,
                        mode=st.session_state.chat_mode,
                        history=history,
                    )
                    if result.get("status") == "approval_required":
                        st.session_state.pending_approval = result.get("interrupt")
                        st.session_state.pending_approval_thread_id = result.get("thread_id") or st.session_state.get("current_thread_id")
                        st.session_state.pending_approval_run_id = result.get("run_id")
                        st.info("SQL approval required. Review the request above.")
                        st.rerun()
                    else:
                        answer = result.get("answer", "")
                        stats = result.get("stats", {})
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer, "stats": stats})
                        _log_message("assistant", answer, run_id=stats.get("run_id"))
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# Main entry
def main():
    """Main application entry point with authentication routing."""
    # Authentication check - renders login/register pages if not authenticated
    is_authenticated = render_auth_routing()
    
    # Only show main app if authenticated
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
                    if st.button("Reset System Database", type="secondary", use_container_width=True, help="This will delete ALL data (history, users, vector store)"):
                        try:
                            with st.spinner("Resetting database..."):
                                AdminService.reset_database()
                            
                            # Clear session state
                            st.session_state.messages = []
                            st.session_state.chat_history = []
                            st.session_state.current_thread_id = None
                            
                            st.success("System reset complete. Please refresh.")
                            time.sleep(1) # Give user a moment to see success
                            st.rerun()
                        except Exception as e:
                            st.error(f"Reset failed: {e}")


if __name__ == "__main__":
    main()