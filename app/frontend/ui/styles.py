"""Page config and global styles."""

from __future__ import annotations

import streamlit as st


def setup_page() -> None:
    st.set_page_config(
        page_title="FPT Policy RAG Agent",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_styles() -> None:
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
