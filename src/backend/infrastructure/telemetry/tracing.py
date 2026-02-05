"""Tiny timing utilities used by telemetry/tracing.

We keep this file intentionally small. LangSmith logic lives in
`backend.infrastructure.telemetry.langsmith`.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def time_block() -> Iterator[callable[[], int]]:
	"""Yield a function returning elapsed ms."""
	start = time.perf_counter()

	def elapsed_ms() -> int:
		return int((time.perf_counter() - start) * 1000)

	yield elapsed_ms

