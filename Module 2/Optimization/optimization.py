"""
Overall CLI - FPT Policy Agent
Production-ready command-line interface for document ingestion and Q&A
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.backend.services.qdrant import vector_db_tool
from app.backend.services.agent_service import AgentService
from app.backend.utils.log import log_info, log_success, log_error, log_warning
from app.backend.api.router import register_all_models
from app.backend.api import form
from app.backend.config import AgentConfig, get_app_config

load_dotenv()
register_all_models()


# ============================================================================
# COMMANDS
# ============================================================================

def ingest(
    path_str: str,
    strategy: str = "recursive",
    pattern: Optional[str] = None
) -> None:
    """
    Ingest documents into vector database
    
    Args:
        path_str: Path to file or directory
        strategy: Chunking strategy (recursive, character, semantic)
        pattern: Optional file pattern for directory ingestion
    """
    path = Path(path_str)
    
    # Validate path exists
    if not path.exists():
        log_error(f"Path not found: {path_str}")
        sys.exit(1)
    
    # Validate chunking strategy
    valid_strategies = {"recursive", "character", "semantic"}
    if strategy not in valid_strategies:
        log_error(f"Invalid strategy: {strategy}. Must be one of: {', '.join(valid_strategies)}")
        sys.exit(1)
    
    try:
        if path.is_file():
            log_info(f"Ingesting file: {path.name}")
            result = vector_db_tool.ingest_file(str(path), chunking_strategy=strategy)
            log_success(f"✓ {result}")
            
        elif path.is_dir():
            log_info(f"Ingesting directory: {path}")
            results = vector_db_tool.ingest_directory(
                str(path),
                recursive=True,
                file_pattern=pattern,
                chunking_strategy=strategy
            )
            
            # Display summary
            print(f"\n{'='*60}")
            print("INGESTION SUMMARY")
            print(f"{'='*60}")
            print(f"Total Files:  {results['total']}")
            print(f"Success:      {results['success']}")
            print(f"Failed:       {results['failed']}")
            print(f"{'='*60}\n")
            
            # Display individual file status
            for file_info in results['files']:
                status_icon = "✓" if file_info['status'] == 'success' else "✗"
                file_name = Path(file_info['path']).name
                print(f"{status_icon} {file_name}")
                if file_info['status'] != 'success' and 'error' in file_info:
                    print(f"  Error: {file_info['error']}")
        
        # Show updated collection info
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
    """
    Ask question using RAG agent
    
    Args:
        question: User's question
        model_name: Optional model name to use
        mode: Agent mode (rag, web, hybrid, chat)
        k: Top-K results for retrieval
        
    Returns:
        Answer string
    """
    # Validate inputs
    if not question or not question.strip():
        log_error("Question cannot be empty")
        sys.exit(1)
    
    if k <= 0:
        log_error("--k must be greater than 0")
        sys.exit(1)
    
    valid_modes = {"rag", "web", "hybrid", "chat"}
    if mode not in valid_modes:
        log_error(f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}")
        sys.exit(1)
    
    # Create agent configuration
    try:
        config = AgentConfig(
            mode=mode,
            top_k=k,
            model_name=model_name
        )
    except ValueError as e:
        log_error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Validate configuration
    is_valid, error_msg = AgentService.validate_config(config)
    if not is_valid:
        log_error(f"Invalid configuration: {error_msg}")
        sys.exit(1)
    
    # Execute query
    try:
        answer, stats = AgentService.execute_query(question, config)
        
        # Log statistics
        log_info(
            f"Tokens: {stats['total_tokens']} "
            f"(in: {stats['total_input_tokens']}, out: {stats['total_output_tokens']}) | "
            f"Cost: ${stats['total_cost']:.6f}"
        )
        
        return answer
        
    except ValueError as e:
        log_error(f"Configuration error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        log_error(f"Execution error: {e}")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)


def status() -> None:
    """Display comprehensive system status"""
    try:
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
        
        print(f"\nSelected Model:  {form.SELECTED_MODEL.name if form.SELECTED_MODEL else 'None'}")
        print(f"Available Models: {', '.join(form.get_all_model_names())}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        log_error(f"Failed to retrieve system status: {e}")
        sys.exit(1)


def serve() -> None:
    """Launch Streamlit web interface"""
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
    log_info(f"Access the web interface at: http://localhost:8501")
    sys.argv = ["streamlit", "run", str(app_path)]
    sys.exit(stcli.main())


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="FPT Policy RAG Agent - Production CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest documents
  python main.py ingest ./documents --strategy semantic
  python main.py ingest policy.pdf --strategy character
  
  # Ask questions
  python main.py ask "What is the vacation policy?"
  python main.py ask "Compare policies" --mode hybrid --k 10
  
  # Check system status
  python main.py status
  
  # Launch web interface
  python main.py serve
"""
    )
    
    subparsers = parser.add_subparsers(dest="cmd", required=True, help="Available commands")
    
    # Ingest command
    ingest_p = subparsers.add_parser(
        "ingest",
        help="Ingest documents into vector database"
    )
    ingest_p.add_argument(
        "path",
        help="File or directory path to ingest"
    )
    ingest_p.add_argument(
        "--strategy",
        choices=["recursive", "character", "semantic"],
        default="semantic",
        help="Chunking strategy (default: semantic)"
    )
    ingest_p.add_argument(
        "--pattern",
        help="File pattern for directory ingestion (e.g., '*.pdf')"
    )
    
    # Ask command
    ask_p = subparsers.add_parser(
        "ask",
        help="Ask a question using the RAG agent"
    )
    ask_p.add_argument(
        "question",
        help="Your question"
    )
    ask_p.add_argument(
        "--model", "-m",
        help="Model name to use (see 'status' for available models)"
    )
    ask_p.add_argument(
        "--mode",
        choices=["rag", "web", "hybrid", "chat"],
        default="rag",
        help="Agent mode (default: rag)"
    )
    ask_p.add_argument(
        "--k",
        type=int,
        default=10,
        help="Top-K results for retrieval (default: 10)"
    )
    
    # Status command
    subparsers.add_parser(
        "status",
        help="Show system status and configuration"
    )
    
    # Serve command
    subparsers.add_parser(
        "serve",
        help="Launch Streamlit web interface"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    try:
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
            
    except KeyboardInterrupt:
        log_warning("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
