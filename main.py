"""Streamlit UI launcher."""

import argparse
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv

from backend.utils.log import log_info, log_error, log_warning
from backend.services.llm.registry import register_all_models
from backend.core.startup import run_startup_tasks

load_dotenv()
register_all_models()
run_startup_tasks()


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


def main() -> None:
    """Main CLI entry point (Streamlit only)."""
    parser = argparse.ArgumentParser(
        description="Streamlit UI Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch web interface
  python main.py serve
"""
    )
    
    subparsers = parser.add_subparsers(dest="cmd", required=True, help="Available commands")
    subparsers.add_parser("serve", help="Launch Streamlit web interface")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    try:
        if args.cmd == "serve":
            serve()
            
    except KeyboardInterrupt:
        log_warning("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
