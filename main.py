"""Application launcher: FastAPI REST API."""

import argparse
import sys
from pathlib import Path


def _bootstrap_src_layout() -> None:
    """Allow running from source without requiring an editable install."""
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


try:
    from utils.log import log_info, log_error, log_warning
except ModuleNotFoundError:
    _bootstrap_src_layout()
    from utils.log import log_info, log_error, log_warning


def api(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Launch FastAPI REST API server via uvicorn."""
    try:
        import uvicorn
    except ImportError:
        log_error("uvicorn not installed (should come with fastapi[standard])")
        print("Install: pip install 'fastapi[standard]'")
        sys.exit(1)

    log_info(f"Launching FastAPI API server on {host}:{port} ...")
    uvicorn.run(
        "core.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Study Roadmap Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch FastAPI REST API
  python main.py api
  python main.py api --port 8080 --reload
"""
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True, help="Available commands")

    api_parser = subparsers.add_parser("api", help="Launch FastAPI REST API server")
    api_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    api_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    try:
        if args.cmd == "api":
            api(host=args.host, port=args.port, reload=args.reload)
            
    except KeyboardInterrupt:
        log_warning("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
