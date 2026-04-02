"""Application-wide concurrency manager.

Provides:
- ThreadPoolExecutor for blocking I/O (DB queries, file system)
- ProcessPoolExecutor for CPU-bound work (document ingestion, chunking)
- Helper methods to dispatch work to either pool from async code

Usage:
    from core.concurrency import concurrency_manager

    result = await concurrency_manager.run_in_thread(blocking_fn, arg1, arg2)
    result = await concurrency_manager.run_in_process(cpu_fn, arg1)
"""

from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Any, Callable, List, Tuple, Dict, TypeVar

from core.settings import get_concurrency_config
from utils.log import log_info, log_debug, log_warning

T = TypeVar("T") # Generic Type Variable - No restrict output


class ConcurrencyManager:
    """Manages thread and process pools for the application lifecycle."""

    def __init__(self) -> None:
        self._thread_pool: ThreadPoolExecutor | None = None
        self._process_pool: ProcessPoolExecutor | None = None
        self._started = False


    def start(self) -> None:
        """Initialize pools. Called during FastAPI lifespan startup."""
        if self._started:
            return

        config = get_concurrency_config()
        self._thread_pool = ThreadPoolExecutor(
            max_workers=config.thread_pool_size,
            thread_name_prefix="app-io",
        )
        self._process_pool = ProcessPoolExecutor(
            max_workers=config.process_pool_size,
        )
        self._started = True
        log_info(
            f"ConcurrencyManager started: "
            f"threads={config.thread_pool_size}, "
            f"processes={config.process_pool_size}"
        )

    def shutdown(self) -> None:
        """Gracefully shut down pools. Called during FastAPI lifespan shutdown."""
        if not self._started:
            return
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)
            log_debug("ThreadPoolExecutor shut down")
        if self._process_pool:
            self._process_pool.shutdown(wait=True)
            log_debug("ProcessPoolExecutor shut down")
        self._started = False
        log_info("ConcurrencyManager shut down")


    async def run_in_thread(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run a blocking callable in the thread pool.

        Ideal for synchronous I/O: database queries, file reads, HTTP calls.
        """
        if not self._started:
            log_warning("ConcurrencyManager not started — running inline")
            return fn(*args, **kwargs)

        loop = asyncio.get_running_loop()
        if kwargs:
            fn = functools.partial(fn, **kwargs)
        return await loop.run_in_executor(self._thread_pool, fn, *args)

    async def run_in_process(self, fn: Callable[..., T], *args: Any) -> T:
        """Run a CPU-bound callable in the process pool.

        Ideal for heavy computation: document parsing, chunking, embeddings.
        Note: ``fn`` and its args must be picklable.
        """
        if not self._started:
            log_warning("ConcurrencyManager not started — running inline")
            return fn(*args)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._process_pool, fn, *args)

    def run_batch_sync(
        self,
        callables: List[Tuple[Callable, tuple, dict]],
        timeout: float | None = None,
    ) -> list:
        """Run multiple blocking callables concurrently from SYNC code.

        Uses ThreadPoolExecutor directly (no event loop required).
        Each entry is ``(fn, args, kwargs)``.
        """
        if not callables:
            return []

        if not self._started or not self._thread_pool:
            return [fn(*args, **kwargs) for fn, args, kwargs in callables]

        futures = []
        for fn, args, kwargs in callables:
            bound = functools.partial(fn, *args, **kwargs)
            futures.append(self._thread_pool.submit(bound))

        return [f.result(timeout=timeout) for f in futures]

    async def run_batch_in_threads(
        self,
        callables: List[Tuple[Callable, tuple, dict]],
        timeout: float | None = None,
    ) -> list:
        """Run multiple blocking callables concurrently from ASYNC code.

        Uses ``asyncio.gather`` + ``loop.run_in_executor``.
        Each entry is ``(fn, args, kwargs)``.
        """
        if not callables:
            return []

        if not self._started or not self._thread_pool:
            return [fn(*args, **kwargs) for fn, args, kwargs in callables]

        loop = asyncio.get_running_loop()
        coros = []
        for fn, args, kwargs in callables:
            bound = functools.partial(fn, *args, **kwargs)
            coros.append(loop.run_in_executor(self._thread_pool, bound))

        if timeout is not None:
            return list(await asyncio.wait_for(
                asyncio.gather(*coros), timeout=timeout,
            ))
        return list(await asyncio.gather(*coros))

    def submit_fire_and_forget(self, fn: Callable[..., Any], *args: Any) -> None:
        """Submit a task to the thread pool without waiting for the result.

        Ideal for background work like cache updates, embedding upserts,
        and disk writes that should not block the caller.
        """
        if not self._started or not self._thread_pool:
            # Fallback: run inline (best effort)
            try:
                fn(*args)
            except Exception as e:
                log_warning(f"Fire-and-forget inline failed: {e}")
            return
        self._thread_pool.submit(fn, *args)

    @property
    def thread_pool(self) -> ThreadPoolExecutor | None:
        return self._thread_pool

    @property
    def process_pool(self) -> ProcessPoolExecutor | None:
        return self._process_pool


# Module-level singleton
concurrency_manager = ConcurrencyManager()
