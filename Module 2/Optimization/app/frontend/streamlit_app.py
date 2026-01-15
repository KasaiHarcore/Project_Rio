"""
Streamlit Web Interface for FPT Policy RAG Agent
Grok-style dark theme: Soft black background, off-white text, muted red accents on edges/borders for subtle highlights without eye strain. Adjusted based on current screenshot for better overrides.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import os

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv, set_key, find_dotenv
from app.backend.services.qdrant import vector_db_tool
from app.backend.services.agent_service import AgentService
from app.backend.api.router import register_all_models
from app.backend.api import form
from app.backend.config import AgentConfig
from app.backend.utils.log import log_info, log_success, log_error  # Assuming these exist; unused in code but kept.

# Load environment
load_dotenv()

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
    "retrieval_k": 5,
    "selected_model": form.get_all_model_names()[0] if form.get_all_model_names() else None,
    "show_settings": False,
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
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
def ask_question(question: str, k: int = 5, mode: str = "rag"):
    config = AgentConfig(mode=mode, top_k=k, model_name=st.session_state.selected_model)
    is_valid, error_msg = AgentService.validate_config(config)
    if not is_valid:
        raise ValueError(f"Invalid configuration: {error_msg}")
    return AgentService.execute_query(question, config)


# UI: Sidebar
def render_sidebar():
    with st.sidebar:
        st.markdown("### FPT Policy Agent")
        st.markdown("---")

        if st.button("New Chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()

        st.markdown("---")
        
        # Moved Settings Menu (Mode/Uploads) here for better layout
        st.markdown("**Chat Mode**")
        mode_map = {"RAG": "rag", "Chat": "chat", "Web Search": "web", "Hybrid": "hybrid"}
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

        if st.session_state.chat_mode == "rag":
            with st.expander("Upload Documents"):
                uploaded_files = st.file_uploader("Add to knowledge base", type=["txt", "md", "pdf"], accept_multiple_files=True, label_visibility="collapsed")
                if uploaded_files and st.button("Upload Files", use_container_width=True):
                    for uploaded_file in uploaded_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            vector_db_tool.ingest_file(tmp_file.name)
                        os.unlink(tmp_file.name)
                        st.success(f"{uploaded_file.name} uploaded")
        
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
        if st.session_state.chat_history:
            for chat in st.session_state.chat_history[-10:]:
                if st.button(f"{chat['title'][:30]}...", key=f"chat_{chat['id']}", use_container_width=True):
                    pass  # TODO: Implement chat loading
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
        if st.button("Settings", use_container_width=True):
            st.session_state.show_settings = not st.session_state.show_settings


# UI: Main chat
def render_chat_interface():
    # Chat messages container
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "stats" in msg:
                with st.expander("Stats"):
                    s = msg["stats"]
                    st.metric("Tokens", s["total_tokens"])
                    st.caption(f"Cost: ${s['total_cost']:.6f}")

    # Standard Streamlit chat input (automatically pinned to bottom)
    prompt = st.chat_input(f"Message FPT Policy Agent ({st.session_state.chat_mode.upper()} mode)...")
    
    # Process user input
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Working on your query... 🚀"):  # Grok-like fun spinner
                try:
                    answer, stats = ask_question(prompt, k=st.session_state.retrieval_k, mode=st.session_state.chat_mode)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer, "stats": stats})
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# Main entry
def main():
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


if __name__ == "__main__":
    main()