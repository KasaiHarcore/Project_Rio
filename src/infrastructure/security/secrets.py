"""Secret management helpers and key loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_loaded = False


def load_secrets(*, dotenv_path: Optional[Path] = None, override: bool = False) -> bool:
	"""Load environment variables from a .env file (idempotent by default)."""
	global _loaded
	if _loaded and not override:
		return True
	loaded = load_dotenv(dotenv_path=dotenv_path, override=override)
	_loaded = True
	return bool(loaded)
