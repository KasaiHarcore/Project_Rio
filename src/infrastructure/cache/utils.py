"""Helpers for stable cache keys and JSON encoding."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def stable_json_dumps(value: Any) -> str:
	"""Deterministic JSON for cache keys."""
	return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_cache_key(*, prefix: str, parts: Dict[str, Any]) -> str:
	payload = stable_json_dumps(parts)
	return f"{prefix}:{sha256_text(payload)}"
