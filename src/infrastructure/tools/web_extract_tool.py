"""Web content extraction tool integration.

Layer 1: Per-run call limit  -> _consume_call()          -- max 4 calls/run (WEB_EXTRACT_MAX_CALLS)
Layer 2: Duplicate detection -> _should_skip_duplicate()  -- skip repeated URL sets in same run
Layer 3: URL count cap       -> per-call configurable     -- max URLs per extract call (default 5, max 20)
Layer 4: Rate limiting       -> _rate_limit()             -- 100ms delay between requests

Uses Tavily Extract API via langchain-tavily to pull full page content from URLs.
Budget friendly: prevents exhausting credits even if model ignores prompts.
"""

import os
import time
import threading
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from langchain_tavily import TavilyExtract
from utils.log import log_success, log_error, log_info, log_warning
from infrastructure.cache import cache_service


class WebExtractTool:
    DEFAULT_EXTRACT_DEPTH = "basic"
    DEFAULT_MAX_CONTENT_LENGTH = 10000
    VALID_EXTRACT_DEPTHS = {"basic", "advanced"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        extract_depth: Literal["basic", "advanced"] = DEFAULT_EXTRACT_DEPTH,
        max_content_length: int = DEFAULT_MAX_CONTENT_LENGTH,
    ):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            log_warning("TAVILY_API_KEY not found. Web extract may fail without API key.")

        self.extract_depth = extract_depth
        self.max_content_length = int(os.getenv("WEB_EXTRACT_MAX_CONTENT_LENGTH", str(max_content_length)))

        self._extract_wrapper: Optional[TavilyExtract] = None
        self._last_extract_time = 0
        self._min_request_interval = 0.1  # 100ms between requests

        self._run_lock = threading.Lock()
        self._default_call_limit = int(os.getenv("WEB_EXTRACT_MAX_CALLS", "4"))
        self._default_max_urls = int(os.getenv("WEB_EXTRACT_MAX_URLS", "5"))
        self._default_dedupe = os.getenv("WEB_EXTRACT_DEDUPE", "True").lower() == "true"
        self._budget_id = 0
        self._run_budget: Dict[str, Any] = {
            "call_limit": self._default_call_limit,
            "call_count": 0,
            "max_urls_cap": max(1, min(20, self._default_max_urls)),
            "dedupe": self._default_dedupe,
            "seen_url_sets": set(),
        }

        log_info(f"WebExtractTool initialized (depth={extract_depth}, max_content={self.max_content_length})")

    def reset_call_limit(self, max_calls: Optional[int] = None) -> None:
        """Reset per-run call limit counter."""
        limit = self._default_call_limit if max_calls is None else int(max_calls)
        with self._run_lock:
            self._budget_id += 1
            self._run_budget["call_limit"] = max(0, limit)
            self._run_budget["call_count"] = 0
            self._run_budget["seen_url_sets"] = set()

    def configure_run(
        self,
        max_calls: Optional[int] = None,
        max_urls: Optional[int] = None,
        dedupe: Optional[bool] = None,
    ) -> None:
        """Configure per-run limits for this tool."""
        self.reset_call_limit(max_calls=max_calls)
        if max_urls is None:
            max_urls_cap = self._default_max_urls
        else:
            max_urls_cap = int(max_urls)
        with self._run_lock:
            self._run_budget["max_urls_cap"] = max(1, min(20, max_urls_cap))
            self._run_budget["dedupe"] = self._default_dedupe if dedupe is None else bool(dedupe)
            self._run_budget["seen_url_sets"] = set()

    def _consume_call(self) -> bool:
        """Return True if another call is allowed, else False."""
        with self._run_lock:
            limit = int(self._run_budget.get("call_limit", self._default_call_limit))
            count = int(self._run_budget.get("call_count", 0))
            if limit <= 0:
                return False
            if count >= limit:
                return False
            self._run_budget["call_count"] = count + 1
            return True

    def _should_skip_duplicate(self, urls: List[str]) -> bool:
        """Skip if the exact same sorted URL set was already extracted in this run."""
        url_key = tuple(sorted(u.strip().lower() for u in urls if u.strip()))
        if not url_key:
            return False
        with self._run_lock:
            if not bool(self._run_budget.get("dedupe", self._default_dedupe)):
                return False
            seen = self._run_budget.get("seen_url_sets")
            if not isinstance(seen, set):
                seen = set()
                self._run_budget["seen_url_sets"] = seen
            if url_key in seen:
                return True
            seen.add(url_key)
            return False

    @property
    def extract_wrapper(self) -> TavilyExtract:
        """Lazy-load Tavily extract wrapper (double-checked locking)."""
        if self._extract_wrapper is None:
            with self._run_lock:
                if self._extract_wrapper is None:
                    try:
                        log_info("Initializing Tavily extract wrapper...")
                        self._extract_wrapper = TavilyExtract(
                            tavily_api_key=self.api_key,
                            extract_depth=self.extract_depth,
                            format="markdown",
                        )
                        log_success("Tavily extract wrapper initialized")
                    except Exception as e:
                        log_error(f"Failed to initialize Tavily extract wrapper: {e}")
                        raise
        return self._extract_wrapper

    def _rate_limit(self):
        """Simple rate limiting to avoid API throttling (Layer 4)."""
        with self._run_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_extract_time
            if time_since_last < self._min_request_interval:
                sleep_time = self._min_request_interval - time_since_last
            else:
                sleep_time = 0
            self._last_extract_time = current_time + sleep_time

        if sleep_time > 0:
            log_info(f"Rate limiting: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)

    def _validate_urls(self, urls: List[str]) -> List[str]:
        """Validate and sanitize URL list."""
        if not urls:
            raise ValueError("URL list cannot be empty")

        cleaned = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
            if not url.startswith(("http://", "https://")):
                log_warning(f"Skipping invalid URL (no http/https): {url[:80]}")
                continue
            cleaned.append(url)

        if not cleaned:
            raise ValueError("No valid URLs provided")

        return cleaned

    def _truncate_content(self, content: str) -> str:
        """Truncate content to max_content_length to protect LLM context window."""
        if not content or len(content) <= self.max_content_length:
            return content
        truncated = content[:self.max_content_length]
        return truncated + f"\n\n[... content truncated at {self.max_content_length} characters]"

    def extract(
        self,
        urls: List[str],
        extract_depth: Optional[Literal["basic", "advanced"]] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract full page content from one or more URLs.

        Args:
            urls: List of URLs to extract content from.
            extract_depth: "basic" for fast text, "advanced" for tables/embedded content.
            query: Optional query to focus extraction on relevant content.

        Returns:
            Dict with status, results (url + raw_content), and failed_results.
        """
        # Validate and cap URLs
        urls = self._validate_urls(urls)
        with self._run_lock:
            max_urls_cap = int(self._run_budget.get("max_urls_cap", self._default_max_urls))
        if len(urls) > max_urls_cap:
            log_warning(f"URL count {len(urls)} exceeds cap {max_urls_cap}, trimming")
            urls = urls[:max_urls_cap]

        effective_depth = extract_depth or self.extract_depth
        if effective_depth not in self.VALID_EXTRACT_DEPTHS:
            log_warning(f"Invalid extract_depth '{effective_depth}', defaulting to 'basic'")
            effective_depth = "basic"

        cache_params = {
            "extract_depth": effective_depth,
            "query": query or "",
        }

        # Check cache
        try:
            cached = cache_service.get_extract_cache(urls=urls, params=cache_params)
            if cached and cached.result:
                log_info("Returning cached extract result")
                return cached.result
        except Exception:
            pass

        # Layer 2: Skip duplicate URL sets within same run
        if self._should_skip_duplicate(urls):
            log_info(f"Skipping duplicate URL set in same run: {urls[:2]}...")
            return {
                "status": "skipped",
                "message": "Duplicate URL set in same run",
                "results": [],
                "failed_results": [],
                "timestamp": datetime.now().isoformat(),
            }

        # Layer 1: Per-run call limit enforcement
        if not self._consume_call():
            log_warning("Per-run extract call limit reached")
            return {
                "status": "limit_reached",
                "message": "Per-run extract call limit reached",
                "results": [],
                "failed_results": [],
                "timestamp": datetime.now().isoformat(),
            }

        try:
            cache_service.mark_tool_call(tool_name="web_extract", params={"urls": sorted(urls), **cache_params})
        except Exception:
            pass

        log_info(f"Extracting {len(urls)} URL(s) (depth={effective_depth}, query={query or 'none'})")

        try:
            self._rate_limit()

            # Build invocation payload
            invoke_input = {"urls": urls}
            if effective_depth != self.extract_depth:
                invoke_input["extract_depth"] = effective_depth
            if query:
                invoke_input["query"] = query

            wrapper = self.extract_wrapper
            raw_result = wrapper.invoke(invoke_input)

            formatted = self._format_results(raw_result, urls)

            # Cache result (best-effort)
            try:
                cache_service.set_extract_cache(urls=urls, params=cache_params, result=formatted)
            except Exception:
                pass

            result_count = len(formatted.get("results", []))
            failed_count = len(formatted.get("failed_results", []))
            log_success(f"Extract completed: {result_count} success, {failed_count} failed")

            return formatted

        except Exception as e:
            log_error(f"Extract failed for {urls[:2]}...: {e}")

        return {
            "status": "error",
            "message": "Extract failed",
            "error": str(e) if 'e' in dir() else "Unknown error",
            "results": [],
            "failed_results": [{"url": u, "error": "Extract failed"} for u in urls],
            "timestamp": datetime.now().isoformat(),
        }

    def _format_results(self, raw_results: Any, urls: List[str]) -> Dict[str, Any]:
        """Format raw extract results into structured output."""
        formatted: Dict[str, Any] = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "results": [],
            "failed_results": [],
        }

        if isinstance(raw_results, dict):
            for item in raw_results.get("results", []):
                if isinstance(item, dict):
                    content = item.get("raw_content", "") or item.get("content", "")
                    formatted["results"].append({
                        "url": item.get("url", ""),
                        "raw_content": self._truncate_content(content),
                    })
            for item in raw_results.get("failed_results", []):
                if isinstance(item, dict):
                    formatted["failed_results"].append({
                        "url": item.get("url", ""),
                        "error": item.get("error", "Unknown error"),
                    })

        elif isinstance(raw_results, str):
            # TavilyExtract may return a string directly
            formatted["results"].append({
                "url": urls[0] if urls else "",
                "raw_content": self._truncate_content(raw_results),
            })

        elif isinstance(raw_results, list):
            for idx, item in enumerate(raw_results):
                if isinstance(item, dict):
                    content = item.get("raw_content", "") or item.get("content", "")
                    formatted["results"].append({
                        "url": item.get("url", urls[idx] if idx < len(urls) else ""),
                        "raw_content": self._truncate_content(content),
                    })
                elif isinstance(item, str):
                    formatted["results"].append({
                        "url": urls[idx] if idx < len(urls) else "",
                        "raw_content": self._truncate_content(item),
                    })

        return formatted


web_extract_tool = WebExtractTool()
