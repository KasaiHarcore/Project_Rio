"""
RAG Basic CLI - FPT Policy Agent
Production-ready command-line interface for document ingestion and Q&A
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from app.backend.services.qdrant import vector_db_tool
from app.backend.services.web_search import web_search_tool
from app.backend.utils.log import log_info, log_success, log_error, log_warning
from app.backend.api.router import register_all_models
from app.backend.api.form import SELECTED_MODEL, set_model, get_all_model_names

load_dotenv()
register_all_models()


class RetrieveInput(BaseModel):
    query: str = Field(..., description="Search query for policy documents")


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Web search query")
    max_results: int = Field(default=5, description="Number of results (1-20)")
    topic: str = Field(default="general", description="Topic: 'general' or 'news'")
    time_range: Optional[str] = Field(default=None, description="Time filter: 'day', 'week', 'month', 'year'")


# ============================================================================
# COMMANDS
# ============================================================================

def ingest(path_str: str, strategy: str = "recursive", pattern: Optional[str] = None) -> None:
    """Ingest documents into vector database"""
    path = Path(path_str)
    
    if not path.exists():
        log_error(f"Path not found: {path_str}")
        sys.exit(1)
    
    try:
        if path.is_file():
            log_info(f"Ingesting file: {path.name}")
            result = vector_db_tool.ingest_file(str(path), chunking_strategy=strategy)
            print(f"✓ {result}")
            
        elif path.is_dir():
            log_info(f"Ingesting directory: {path}")
            results = vector_db_tool.ingest_directory(
                str(path),
                recursive=True,
                file_pattern=pattern,
                chunking_strategy=strategy
            )
            
            print(f"\n{'='*60}")
            print("INGESTION SUMMARY")
            print(f"{'='*60}")
            print(f"Total Files:  {results['total']}")
            print(f"Success:      {results['success']}")
            print(f"Failed:       {results['failed']}")
            print(f"{'='*60}\n")
            
            for file_info in results['files']:
                status_icon = "✓" if file_info['status'] == 'success' else "✗"
                print(f"{status_icon} {Path(file_info['path']).name}")
        
        info = vector_db_tool.get_collection_info()
        log_success(f"Collection now has {info.get('vectors_count', 0)} vectors")
        
    except Exception as e:
        log_error(f"Ingestion failed: {e}")
        sys.exit(1)


def ask(
    question: str, 
    model_name: Optional[str] = None,
    mode: str = "rag",
    k: int = 5
) -> str:
    """Ask question with optional web search"""
    if model_name:
        set_model(model_name)
    
    if not SELECTED_MODEL.llm:
        SELECTED_MODEL.setup()
    
    tools = []
    
    # RAG mode - add vector search tool
    if mode in {"rag", "hybrid"}:
        retriever_tool = StructuredTool.from_function(
            name="policy_retriever",
            description="Search FPT policy knowledge base. Use for internal policies and procedures.",
            func=lambda query: vector_db_tool.search_documents(query, k=k),
            args_schema=RetrieveInput,
        )
        tools.append(retriever_tool)
    
    # Web search mode - add web search tool
    if mode in {"web", "hybrid"}:
        tools.append(web_search_tool.get_search_tool())
    
    if not tools:
        log_error(f"Invalid mode: {mode}")
        sys.exit(1)
    
    log_info(f"Creating agent with {len(tools)} tool(s) using {SELECTED_MODEL.name}")
    agent = create_react_agent(SELECTED_MODEL.llm, tools=tools)
    
    system_prompts = {
        "rag": (
            "You are a RAG agent for FPT internal policies.\n"
            "ALWAYS use policy_retriever first. Answer only from retrieved context.\n"
            "Cite sources when available. Be concise and accurate."
        ),
        "web": (
            "You are a web research assistant.\n"
            "Use web_search to find current information. Cite URLs in your answers.\n"
            "Be factual and include sources."
        ),
        "hybrid": (
            "You are a hybrid research assistant.\n"
            "- Use policy_retriever for FPT internal policies\n"
            "- Use web_search for external/current information\n"
            "Always cite sources with URLs when available."
        )
    }
    
    result = agent.invoke({
        "messages": [
            ("system", system_prompts[mode]),
            HumanMessage(content=question),
        ]
    })
    
    messages = result.get("messages", [])
    answer = getattr(messages[-1], "content", "") if messages else ""
    
    stats = SELECTED_MODEL.get_overall_exec_stats()
    log_info(
        f"Tokens: {stats['total_tokens']} "
        f"(in: {stats['total_input_tokens']}, out: {stats['total_output_tokens']}) | "
        f"Cost: ${stats['total_cost']:.6f}"
    )
    
    return answer


def status() -> None:
    """Show system status"""
    info = vector_db_tool.get_collection_info()
    
    print(f"\n{'='*70}")
    print("SYSTEM STATUS")
    print(f"{'='*70}")
    print(f"Collection:      {info['collection_name']}")
    print(f"Status:          {info['status']}")
    print(f"Vectors:         {info.get('vectors_count', 'N/A')}")
    print(f"Storage:         {info['persist_dir']}")
    print(f"Embedding:       {info['embedding_model']}")
    print(f"Chunk Size:      {info['chunk_size']}")
    print(f"Chunk Overlap:   {info['chunk_overlap']}")
    
    if 'vector_dimension' in info:
        print(f"Vector Dim:      {info['vector_dimension']}")
    if 'distance_metric' in info:
        print(f"Distance:        {info['distance_metric']}")
    
    print(f"\nSelected Model:  {SELECTED_MODEL.name if SELECTED_MODEL else 'None'}")
    print(f"Available Models: {', '.join(get_all_model_names())}")
    print(f"{'='*70}\n")


def serve() -> None:
    """Launch Streamlit UI"""
    try:
        import streamlit.web.cli as stcli
    except ImportError:
        log_error("Streamlit not installed")
        print("Install: pip install streamlit")
        sys.exit(1)
    
    app_path = Path(__file__).parent / "app" / "frontend" / "streamlit_app.py"
    
    if not app_path.exists():
        log_error(f"UI not found: {app_path}")
        sys.exit(1)
    
    log_info("Launching Streamlit UI...")
    sys.argv = ["streamlit", "run", str(app_path)]
    sys.exit(stcli.main())


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="FPT Policy RAG Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    
    # Ingest
    ingest_p = subparsers.add_parser("ingest", help="Ingest documents")
    ingest_p.add_argument("path", help="File or directory path")
    ingest_p.add_argument("--strategy", choices=["recursive", "character"], default="recursive")
    ingest_p.add_argument("--pattern", help="File pattern (e.g., '*.pdf')")
    
    # Ask
    ask_p = subparsers.add_parser("ask", help="Ask question")
    ask_p.add_argument("question", help="Your question")
    ask_p.add_argument("--model", "-m", help="Model name")
    ask_p.add_argument("--mode", choices=["rag", "web", "hybrid"], default="rag")
    ask_p.add_argument("--k", type=int, default=5, help="Top-K results")
    
    # Status
    subparsers.add_parser("status", help="Show system status")
    
    # Serve
    subparsers.add_parser("serve", help="Launch web UI")
    
    args = parser.parse_args()
    
    if args.cmd == "ingest":
        ingest(args.path, args.strategy, args.pattern)
    
    elif args.cmd == "ask":
        answer = ask(args.question, args.model, args.mode, args.k)
        print(f"\n{'='*70}")
        print("ANSWER")
        print(f"{'='*70}")
        print(answer)
        print(f"{'='*70}\n")
    
    elif args.cmd == "status":
        status()
    
    elif args.cmd == "serve":
        serve()


if __name__ == "__main__":
    main()
