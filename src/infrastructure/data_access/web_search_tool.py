"""Web search tool integration.

Layer 1: Per-run call limit  → _consume_call()       — max 6 calls/run (WEB_SEARCH_MAX_CALLS)
Layer 2: Duplicate detection → _should_skip_duplicate() — skip repeated queries in same run
Layer 3: Time window limit   → _check_search_limit() — max N searches/hour (optional)
Layer 4: Rate limiting       → _rate_limit()          — 100ms delay between requests
Layer 5: Max results cap     → per-run configurable   — max results per search (default 5, max 20)

- Allowed full search with cache, rate limit, formatting.
- Budget friendly: prevent exhausting credits even if model ignores prompts.
"""

import os
import re
import time
import threading
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from urllib.parse import urlparse
from langchain_tavily import TavilySearch
from utils.log import log_success, log_error, log_info, log_warning
from infrastructure.cache import cache_service
from services import source_capture

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

class WebSearchTool:
    DEFAULT_MAX_RESULTS = 5
    DEFAULT_TOPIC = "general"
    DEFAULT_MAX_SEARCHES = 5
    DEFAULT_WINDOW_SECONDS = 3600
    
    VALID_TOPICS = {"general", "news"}
    VALID_TIME_RANGES = {"day", "week", "month", "year"}
    VALID_SEARCH_DEPTHS = {"basic", "advanced", "fast", "ultra-fast"}
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        search_depth: Literal["basic", "advanced"] = "basic",
        include_raw_content: bool = False,
        include_images: bool = False
    ):
        """
        Initialize WebSearchTool
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            log_warning("TAVILY_API_KEY not found. Web search may fail without API key.")
        
        self.max_results = max_results
        self.search_depth = search_depth
        self.include_raw_content = include_raw_content
        self.include_images = include_images
        self._max_searches = int(os.getenv("TAVILY_MAX_SEARCHES", self.DEFAULT_MAX_SEARCHES))
        self._window_seconds = int(os.getenv("TAVILY_WINDOW_SECONDS", self.DEFAULT_WINDOW_SECONDS))
        self._window_start = time.time()
        self._search_count = 0
        self._enforce_window_limit = os.getenv("TAVILY_ENFORCE_WINDOW_LIMIT", "False").lower() == "true"
        
        self._search_wrapper: Optional[TavilySearch] = None
        self._last_search_time = 0
        self._min_request_interval = 0.1  # 100ms between requests

        self._run_lock = threading.Lock()
        self._default_call_limit = int(os.getenv("WEB_SEARCH_MAX_CALLS", "6"))
        self._default_max_results = int(os.getenv("WEB_SEARCH_MAX_RESULTS", str(self.max_results)))
        self._default_dedupe = os.getenv("WEB_SEARCH_DEDUPE", "True").lower() == "true"
        self._budget_id = 0
        self._run_budget: Dict[str, Any] = {
            "call_limit": self._default_call_limit,
            "call_count": 0,
            "max_results_cap": max(1, min(20, self._default_max_results)),
            "dedupe": self._default_dedupe,
            "seen_queries": set(),
        }
        
        log_info(f"WebSearchTool initialized (depth={search_depth}, max_results={max_results})")

    def reset_call_limit(self, max_calls: Optional[int] = None) -> None:
        """Reset per-run call limit counter for this tool."""
        limit = self._default_call_limit if max_calls is None else int(max_calls)
        with self._run_lock:
            self._budget_id += 1
            self._run_budget["call_limit"] = max(0, limit)
            self._run_budget["call_count"] = 0
            self._run_budget["seen_queries"] = set()

    def configure_run(
        self,
        max_calls: Optional[int] = None,
        max_results: Optional[int] = None,
        dedupe: Optional[bool] = None,
    ) -> None:
        """Configure per-run limits for this tool.

        This is the primary enforcement layer to prevent the model from exhausting
        credits even if it ignores prompt guidance.
        """
        self.reset_call_limit(max_calls=max_calls)
        if max_results is None:
            max_results_cap = self._default_max_results
        else:
            max_results_cap = int(max_results)
        with self._run_lock:
            self._run_budget["max_results_cap"] = max(1, min(20, max_results_cap))
            self._run_budget["dedupe"] = self._default_dedupe if dedupe is None else bool(dedupe)
            self._run_budget["seen_queries"] = set()

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

    def _should_skip_duplicate(self, query: str) -> bool:
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return False
        with self._run_lock:
            if not bool(self._run_budget.get("dedupe", self._default_dedupe)):
                return False
            seen = self._run_budget.get("seen_queries")
            if not isinstance(seen, set):
                seen = set()
                self._run_budget["seen_queries"] = seen
            if normalized_query in seen:
                return True
            seen.add(normalized_query)
            return False

    def _check_search_limit(self) -> None:
        """Enforce max searches within time window (Layer 3)."""
        if not self._enforce_window_limit:
            return
        with self._run_lock:
            now = time.time()
            if now - self._window_start > self._window_seconds:
                self._window_start = now
                self._search_count = 0
            if self._search_count >= self._max_searches:
                raise ValueError(
                    f"Search limit reached: {self._max_searches} per {self._window_seconds} seconds"
                )
            self._search_count += 1
    
    @property
    def search_wrapper(self) -> TavilySearch:
        """Lazy-load Tavily search wrapper (double-checked locking)."""
        if self._search_wrapper is None:
            with self._run_lock:
                if self._search_wrapper is None:
                    try:
                        log_info("Initializing Tavily search wrapper...")
                        self._search_wrapper = TavilySearch(
                            tavily_api_key=self.api_key,
                            max_results=self.max_results,
                            topic=self.DEFAULT_TOPIC,
                            include_answer=True,
                            search_depth=self.search_depth,
                            include_raw_content=self.include_raw_content,
                            include_images=self.include_images
                        )
                        log_success("Tavily search wrapper initialized")
                    except Exception as e:
                        log_error(f"Failed to initialize Tavily wrapper: {e}")
                        raise
        return self._search_wrapper
    
    def _rate_limit(self):
        """Simple rate limiting to avoid API throttling (Layer 4)."""
        with self._run_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_search_time
            if time_since_last < self._min_request_interval:
                sleep_time = self._min_request_interval - time_since_last
            else:
                sleep_time = 0
            # Reserve this time slot so concurrent threads queue behind us
            self._last_search_time = current_time + sleep_time

        if sleep_time > 0:
            log_info(f"Rate limiting: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)
    
    def _validate_params(
        self,
        query: str,
        max_results: int,
        topic: str,
        time_range: Optional[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[str, int, str, Optional[str], Optional[str], Optional[str]]:
        """Validate and sanitize search parameters."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        query = query.strip()

        if max_results < 1 or max_results > 20:
            log_warning(f"max_results {max_results} out of range, clamping to [1, 20]")
            max_results = max(1, min(20, max_results))

        if topic not in self.VALID_TOPICS:
            log_warning(f"Invalid topic '{topic}', defaulting to 'general'")
            topic = "general"

        if time_range and time_range not in self.VALID_TIME_RANGES:
            log_warning(f"Invalid time_range '{time_range}', ignoring")
            time_range = None

        if start_date and not _DATE_RE.match(start_date):
            log_warning(f"Invalid start_date '{start_date}' (expected YYYY-MM-DD), ignoring")
            start_date = None

        if end_date and not _DATE_RE.match(end_date):
            log_warning(f"Invalid end_date '{end_date}' (expected YYYY-MM-DD), ignoring")
            end_date = None

        return query, max_results, topic, time_range, start_date, end_date
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        topic: str = DEFAULT_TOPIC,
        time_range: Optional[str] = None,
        search_depth: Optional[Literal["basic", "advanced", "fast", "ultra-fast"]] = None,
        include_answer: bool = True,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_raw_content: bool = False,
    ) -> Dict[str, Any]:
        """
        Perform web search with comprehensive options
        """
        with self._run_lock:
            max_results_cap = int(self._run_budget.get("max_results_cap", self._default_max_results))
        max_results = max_results or self.max_results
        max_results = min(max_results, max_results_cap)
        effective_search_depth = search_depth or self.search_depth
        
        # Validate parameters
        query, max_results, topic, time_range, start_date, end_date = self._validate_params(
            query, max_results, topic, time_range, start_date, end_date
        )

        cache_params = {
            "max_results": int(max_results),
            "topic": topic,
            "time_range": time_range,
            "search_depth": effective_search_depth,
            "include_domains": include_domains or [],
            "exclude_domains": exclude_domains or [],
            "start_date": start_date,
            "end_date": end_date,
        }
        try:
            cached = cache_service.get_web_cache(query=query, params=cache_params)
            if cached and cached.result:
                log_info("Returning cached web search result")
                return cached.result
        except Exception:
            pass

        # Layer 2: Skip duplicate queries within same run
        if self._should_skip_duplicate(query):
            log_info(f"Skipping duplicate query in same run: '{query}'")
            return {
                "query": query,
                "status": "skipped",
                "message": "Duplicate query in same run",
                "results": [],
                "timestamp": datetime.now().isoformat()
            }

        # Layer 1: Per-run call limit enforcement
        if not self._consume_call():
            log_warning(f"Per-run call limit reached, rejecting: '{query}'")
            return {
                "query": query,
                "status": "limit_reached",
                "message": "Per-run search call limit reached",
                "results": [],
                "timestamp": datetime.now().isoformat()
            }

        try:
            cache_service.mark_tool_call(tool_name="web_search", params={"query": query, **cache_params})
        except Exception:
            pass
        
        log_info(
            f"Searching: '{query}' (max={max_results}, topic={topic}, time={time_range}, depth={effective_search_depth})"
        )
        
        try:
            self._rate_limit()
            self._check_search_limit()
            
            # Build search kwargs (only per-request supported fields)
            search_kwargs = {
                "query": query,
                "topic": topic  # Can override
            }

            if effective_search_depth in self.VALID_SEARCH_DEPTHS:
                search_kwargs["search_depth"] = effective_search_depth
            
            if time_range:
                search_kwargs["time_range"] = time_range  # Fixed: Use string "time_range" (no int conversion)
            
            if include_domains:
                search_kwargs["include_domains"] = include_domains
            
            if exclude_domains:
                search_kwargs["exclude_domains"] = exclude_domains

            if start_date:
                search_kwargs["start_date"] = start_date

            if end_date:
                search_kwargs["end_date"] = end_date

            if include_raw_content:
                search_kwargs["include_raw_content"] = True

            # Perform search (compat with TavilySearch tool variants)
            wrapper = self.search_wrapper
            if hasattr(wrapper, "results"):
                results = wrapper.results(**search_kwargs)
            elif hasattr(wrapper, "search"):
                results = wrapper.search(**search_kwargs)
            else:
                results = wrapper.invoke(search_kwargs)
            
            # Format results
            formatted = self._format_results(results, query)

            # Cache formatted result (best-effort)
            try:
                cache_service.set_web_cache(query=query, params=cache_params, result=formatted)
            except Exception:
                pass
            
            log_success(f"Search completed: {len(formatted.get('results', []))} results found")
            
            return formatted

        except ValueError as e:
            error_msg = str(e)
            if "Search limit reached" in error_msg:
                log_warning(f"Search limit reached for '{query}'")
            else:
                log_error(f"Search failed for '{query}': {e}")
        except Exception as e:
            log_error(f"Search failed for '{query}': {e}")

        return {
            "query": query,
            "status": "no_results",
            "message": "No information found",
            "error": "Search failed",
            "results": [],
            "timestamp": datetime.now().isoformat()
        }
    
    def _format_results(self, raw_results: Any, query: str) -> Dict[str, Any]:
        """Format raw search results into structured output"""
        formatted = {
            "query": query,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "results": []
        }
        
        # Handle different result formats
        if isinstance(raw_results, dict):
            # Extract answer if available
            if "answer" in raw_results:
                formatted["answer"] = raw_results["answer"]
            
            # Extract results
            if "results" in raw_results:
                for idx, result in enumerate(raw_results["results"], 1):
                    formatted_result = {
                        "rank": idx,
                        "title": result.get("title", "No title"),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0)
                    }

                    # Optional fields
                    if "published_date" in result:
                        formatted_result["published_date"] = result["published_date"]

                    if "raw_content" in result and result["raw_content"]:
                        formatted_result["raw_content"] = result["raw_content"]

                    formatted["results"].append(formatted_result)

                    _capture_web_source(formatted_result)
        
        elif isinstance(raw_results, list):
            for idx, result in enumerate(raw_results, 1):
                if isinstance(result, dict):
                    entry = {
                        "rank": idx,
                        "title": result.get("title", "No title"),
                        "url": result.get("url", ""),
                        "content": result.get("content", "")
                    }
                    formatted["results"].append(entry)
                    _capture_web_source(entry)

        return formatted


def _capture_web_source(result: Dict[str, Any]) -> None:
    """Push a normalized web-source payload onto the per-stream accumulator."""
    url = result.get("url") or ""
    if not url:
        return
    try:
        host = urlparse(url).hostname or url
        if host.startswith("www."):
            host = host[4:]
    except Exception:
        host = url
    snippet_raw = result.get("content") or ""
    source_capture.append({
        "kind": "web",
        "url": url,
        "title": result.get("title") or url,
        "snippet": snippet_raw[:300],
        "site_name": host,
        "timestamp": time.time() * 1000,
    })


web_search_tool = WebSearchTool()