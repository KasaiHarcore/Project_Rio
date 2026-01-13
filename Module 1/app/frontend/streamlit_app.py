"""
Streamlit Web Interface for FPT Policy RAG Agent
Production-ready OpenAI-style chat interface
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from dotenv import load_dotenv, set_key, find_dotenv
import tempfile
import os

from app.backend.services.qdrant import vector_db_tool
from app.backend.api.router import register_all_models
from app.backend.api.form import SELECTED_MODEL, set_model, get_all_model_names
from app.backend.utils.log import log_info, log_success, log_error

# Load environment
load_dotenv()

# Register models
if "models_registered" not in st.session_state:
    register_all_models()
    st.session_state.models_registered = True

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = "RAG"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Page config
st.set_page_config(
    page_title="FPT Policy RAG Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - OpenAI-inspired
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        max-width: 100%;
    }
    
    /* Mode selector */
    .mode-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        background: #e3f2fd;
        color: #1976d2;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    /* Sidebar sections */
    .sidebar-section {
        padding: 1rem 0;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .sidebar-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #666;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


class RetrieveInput(BaseModel):
    query: str = Field(..., description="Question to search in FPT policy knowledge base")


def ask_question(question: str, k: int = 5, mode: str = "RAG"):
    """Process question through ReAct agent"""
    if not SELECTED_MODEL.llm:
        SELECTED_MODEL.setup()
    
    tools = []
    
    if mode == "RAG":
        retriever_tool = StructuredTool.from_function(
            name="policy_retriever",
            description=(
                "Searches the FPT internal policy knowledge base (VectorDB) and returns "
                "the most relevant excerpts. ALWAYS use this tool before answering questions."
            ),
            func=lambda query: vector_db_tool.search_documents(query, k=k),
            args_schema=RetrieveInput,
        )
        tools.append(retriever_tool)
    
    agent = create_react_agent(SELECTED_MODEL.llm, tools=tools)
    
    if mode == "RAG":
        system_prompt = (
            "You are a RAG agent specialized in answering questions about FPT internal policies.\n"
            "ALWAYS use the policy_retriever tool first. Answer ONLY based on retrieved context. "
            "Cite sources when available. Be concise and accurate."
        )
    else:
        system_prompt = "You are a helpful AI assistant. Provide clear and accurate answers."
    
    result = agent.invoke({
        "messages": [
            ("system", system_prompt),
            HumanMessage(content=question),
        ]
    })
    
    messages = result.get("messages", [])
    answer = getattr(messages[-1], "content", "") if messages else ""
    stats = SELECTED_MODEL.get_overall_exec_stats()
    return answer, stats


def render_sidebar():
    """Render OpenAI-style sidebar"""
    with st.sidebar:
        # Header
        st.markdown("### 📚 FPT Policy Agent")
        st.markdown("---")
        
        # New Chat Button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.session_state.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()
        
        st.markdown("---")
        
        # Overall Status Section
        with st.expander("📊 Overall Status", expanded=False):
            try:
                info = vector_db_tool.get_collection_info()
                st.metric("Vector Count", info.get("vectors_count", "N/A"))
                st.metric("Collection", info["collection_name"])
                st.caption(f"**Model:** {SELECTED_MODEL.name if SELECTED_MODEL else 'Not initialized'}")
            except:
                st.warning("Status unavailable")
        
        # Chat History Section
        st.markdown('<div class="sidebar-title">Chat History</div>', unsafe_allow_html=True)
        
        # Search chat
        search_query = st.text_input("🔍 Search chats", placeholder="Search...", label_visibility="collapsed")
        
        # Display chat history (placeholder for now)
        if st.session_state.chat_history:
            for chat in st.session_state.chat_history[-10:]:  # Show last 10
                if st.button(f"💬 {chat['title'][:30]}...", key=f"chat_{chat['id']}", use_container_width=True):
                    # Load chat functionality (to be implemented)
                    pass
        else:
            st.caption("No chat history yet")
        
        st.markdown("---")
        
        # User Section
        with st.expander("👤 User Settings", expanded=False):
            # API Keys
            st.markdown("**API Keys**")
            
            # Initialize API keys in session state
            if "openai_api_key" not in st.session_state:
                st.session_state.openai_api_key = os.getenv("OPENAI_API_KEY", "")
            if "openrouter_api_key" not in st.session_state:
                st.session_state.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
            
            # OpenAI API Key
            openai_key = st.text_input(
                "OpenAI API Key",
                value=st.session_state.openai_api_key,
                type="password",
                placeholder="sk-...",
                help="Your OpenAI API key"
            )
            if openai_key != st.session_state.openai_api_key:
                st.session_state.openai_api_key = openai_key
                os.environ["OPENAI_API_KEY"] = openai_key
                # Save to .env file
                env_file = find_dotenv()
                if env_file:
                    set_key(env_file, "OPENAI_API_KEY", openai_key)
                    st.success("✓ OpenAI key updated")
            
            # OpenRouter API Key
            openrouter_key = st.text_input(
                "OpenRouter API Key",
                value=st.session_state.openrouter_api_key,
                type="password",
                placeholder="sk-or-...",
                help="Your OpenRouter API key"
            )
            if openrouter_key != st.session_state.openrouter_api_key:
                st.session_state.openrouter_api_key = openrouter_key
                os.environ["OPENROUTER_API_KEY"] = openrouter_key
                # Save to .env file
                env_file = find_dotenv()
                if env_file:
                    set_key(env_file, "OPENROUTER_API_KEY", openrouter_key)
                    st.success("✓ OpenRouter key updated")
            
            st.markdown("---")
            
            # Model selection
            st.markdown("**Model Selection**")
            available_models = get_all_model_names()
            
            if "selected_model" not in st.session_state:
                st.session_state.selected_model = available_models[0] if available_models else None
            
            selected = st.selectbox(
                "Choose LLM",
                options=available_models,
                index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
                label_visibility="collapsed"
            )
            
            if selected != st.session_state.selected_model:
                st.session_state.selected_model = selected
                set_model(selected)
                st.success(f"✓ Switched to {selected}")
            
            st.markdown("---")
            
            # Retrieval settings
            st.markdown("**Retrieval Settings**")
            st.session_state.retrieval_k = st.slider(
                "Top-K Results",
                min_value=1,
                max_value=10,
                value=st.session_state.get("retrieval_k", 5)
            )
        
        st.markdown("---")
        
        # Settings
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.show_settings = not st.session_state.get("show_settings", False)


def render_mode_selector():
    """Render mode selector"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        mode = st.selectbox(
            "Mode",
            options=["RAG", "Chat", "Web Search"],
            index=["RAG", "Chat", "Web Search"].index(st.session_state.chat_mode),
            label_visibility="collapsed",
            key="mode_selector"
        )
        if mode != st.session_state.chat_mode:
            st.session_state.chat_mode = mode
    
    with col2:
        if st.session_state.chat_mode == "RAG":
            with st.popover("📄"):
                st.markdown("**Upload Documents**")
                uploaded_files = st.file_uploader(
                    "Add to knowledge base",
                    type=["txt", "md", "pdf"],
                    accept_multiple_files=True,
                    label_visibility="collapsed"
                )
                
                if uploaded_files and st.button("Upload"):
                    for uploaded_file in uploaded_files:
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                                tmp_file.write(uploaded_file.getbuffer())
                                tmp_path = tmp_file.name
                            
                            vector_db_tool.ingest_file(tmp_path)
                            os.unlink(tmp_path)
                            st.success(f"✓ {uploaded_file.name}")
                        except Exception as e:
                            st.error(f"✗ {uploaded_file.name}: {str(e)}")


def render_chat_interface():
    # Mode badge
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:4px 10px;
            border-radius:12px;
            font-size:0.85rem;
            background:#e3f2fd;
            color:#1976d2;
            margin-bottom:8px;
        ">
            {st.session_state.chat_mode} Mode
        </div>
        """,
        unsafe_allow_html=True
    )

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant" and "stats" in msg:
                with st.expander("📊 Stats"):
                    s = msg["stats"]
                    st.metric("Tokens", s["total_tokens"])
                    st.caption(f"Cost: ${s['total_cost']:.6f}")

    # Input (LET STREAMLIT HANDLE POSITION)
    prompt = st.chat_input("Message FPT Policy Agent…")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer, stats = ask_question(
                    prompt,
                    k=st.session_state.get("retrieval_k", 5),
                    mode=st.session_state.chat_mode
                )
                st.markdown(answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "stats": stats
        })


def main():
    """Main application entry point"""
    render_sidebar()
    
    # Main content area
    st.markdown("## 💬 Chat")
    
    # Mode selector
    render_mode_selector()
    
    # Chat interface
    render_chat_interface()
    
    # Settings modal
    if st.session_state.get("show_settings", False):
        with st.expander("⚙️ Advanced Settings", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Storage Settings**")
                st.code(f"Path: {vector_db_tool.persist_dir}")
                st.code(f"Collection: {vector_db_tool.collection_name}")
            
            with col2:
                st.markdown("**Model Settings**")
                st.code(f"Embedding: {vector_db_tool.model_name}")
                if SELECTED_MODEL:
                    st.code(f"LLM: {SELECTED_MODEL.name}")


if __name__ == "__main__":
    main()
