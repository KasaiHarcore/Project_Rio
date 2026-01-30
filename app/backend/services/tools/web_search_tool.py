"""Web search tool integration."""

import os
import time
import threading
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from langchain_tavily import TavilySearch
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from backend.utils.log import log_success, log_error, log_info, log_warning
from backend.cache import cache_service

class WebSearchTool:
    DEFAULT_MAX_RESULTS = 5
    DEFAULT_TOPIC = "general"
    DEFAULT_MAX_SEARCHES = 5
    DEFAULT_WINDOW_SECONDS = 3600
    
    VALID_TOPICS = {"general", "news"}
    VALID_TIME_RANGES = {"day", "week", "month", "year"}
    VALID_SEARCH_DEPTHS = {"basic", "advanced"}
    
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

        # NOTE: Tool calls may run in a threadpool, so thread-local counters are unreliable.
        # Enforce budgets in a shared, lock-protected structure.
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
        """Enforce max searches within time window."""
        if not self._enforce_window_limit:
            return
        now = time.time()
        if now - self._window_start > self._window_seconds:
            self._window_start = now
            self._search_count = 0
        if self._search_count >= self._max_searches:
            raise ValueError(
                f"Search limit reached: {self._max_searches} per {self._window_seconds} seconds"
            )
    
    @property
    def search_wrapper(self) -> TavilySearch:
        """Lazy-load Tavily search wrapper"""
        if self._search_wrapper is None:
            try:
                log_info("Initializing Tavily search wrapper...")
                self._search_wrapper = TavilySearch(
                    tavily_api_key=self.api_key,
                    max_results=self.max_results,  # Added: Set at init (cannot override per request)
                    topic=self.DEFAULT_TOPIC,  # Added: Default topic at init (can override per request)
                    include_answer=True,  # Added: Fixed at init since cannot override per request (matches your default)
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
        """Simple rate limiting to avoid API throttling"""
        current_time = time.time()
        time_since_last = current_time - self._last_search_time
        
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            log_info(f"Rate limiting: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)
        
        self._last_search_time = time.time()
    
    def _validate_params(
        self,
        query: str,
        max_results: int,
        topic: str,
        time_range: Optional[str]
    ) -> tuple[str, int, str, Optional[str]]:
        """Validate and sanitize search parameters"""
        # Validate query
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        query = query.strip()
        
        # Validate max_results
        if max_results < 1 or max_results > 20:
            log_warning(f"max_results {max_results} out of range, clamping to [1, 20]")
            max_results = max(1, min(20, max_results))
        
        # Validate topic
        if topic not in self.VALID_TOPICS:
            log_warning(f"Invalid topic '{topic}', defaulting to 'general'")
            topic = "general"
        
        # Validate time_range
        if time_range and time_range not in self.VALID_TIME_RANGES:
            log_warning(f"Invalid time_range '{time_range}', ignoring")
            time_range = None
        
        return query, max_results, topic, time_range
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        topic: str = DEFAULT_TOPIC,
        time_range: Optional[str] = None,
        search_depth: Optional[Literal["basic", "advanced"]] = None,
        include_answer: bool = True,  # Note: Ignored here since fixed at init; kept for compat
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
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
        query, max_results, topic, time_range = self._validate_params(
            query, max_results, topic, time_range
        )

        cache_params = {
            "max_results": int(max_results),
            "topic": topic,
            "time_range": time_range,
            "search_depth": effective_search_depth,
            "include_domains": include_domains or [],
            "exclude_domains": exclude_domains or [],
        }
        try:
            cached = cache_service.get_web_cache(query=query, params=cache_params)
            if cached and cached.result:
                log_info("Returning cached web search result")
                return cached.result
        except Exception:
            pass

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
            self._search_count += 1
            
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
            if "Search limit reached" in str(e):
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
                    
                    formatted["results"].append(formatted_result)
        
        elif isinstance(raw_results, list):
            for idx, result in enumerate(raw_results, 1):
                if isinstance(result, dict):
                    formatted["results"].append({
                        "rank": idx,
                        "title": result.get("title", "No title"),
                        "url": result.get("url", ""),
                        "content": result.get("content", "")
                    })
        
        return formatted
    
    def search_as_string(
        self,
        query: str,
        max_results: Optional[int] = None,
        topic: str = DEFAULT_TOPIC,
        time_range: Optional[str] = None,
        search_depth: Optional[Literal["basic", "advanced"]] = None,
    ) -> str:
        """
        Perform search and return formatted string (for agent tools)
        """
        result = self.search(query, max_results, topic, time_range, search_depth=search_depth)
        
        if result["status"] != "success" or not result.get("results"):
            return f"No information found for '{query}'."
        
        # Build formatted string
        parts = [f"Search results for: '{query}'\n"]
        
        # Add answer if available
        if "answer" in result:
            parts.append(f"\nQuick Answer:\n{result['answer']}\n")
        
        # Add results
        parts.append("\nTop Results:\n")
        for res in result["results"]:
            parts.append(
                f"\n[{res['rank']}] {res['title']}\n"
                f"URL: {res['url']}\n"
                f"{res['content'][:300]}{'...' if len(res['content']) > 300 else ''}\n"
            )
            if "score" in res:
                parts.append(f"Relevance: {res['score']:.2f}\n")
        
        return "".join(parts)
    
    def get_search_tool(self) -> StructuredTool:
        """Return the primary web search tool."""
        class SearchInput(BaseModel):
            query: str = Field(..., description="The search query")
            max_results: int = Field(default=5, description="Number of results (1-20)")
            topic: str = Field(default="general", description="Search topic: 'general' or 'news'")
            time_range: Optional[str] = Field(default=None, description="Time filter: 'day', 'week', 'month', or 'year'")
            search_depth: Literal["basic", "advanced"] = Field(default="basic", description="Search depth")

        def _run_search(
            query: str,
            max_results: int = 5,
            topic: str = "general",
            time_range: Optional[str] = None,
            search_depth: str = "basic",
        ) -> str:
            if self._should_skip_duplicate(query):
                log_warning(f"Duplicate web search query skipped: '{query}'")
                return (
                    "Duplicate web search query skipped. "
                    "Refine the query (add constraints like site:, date, or specific terms)."
                )

            if not self._consume_call():
                with self._run_lock:
                    limit = int(self._run_budget.get("call_limit", self._default_call_limit))
                log_warning(f"Web search call limit reached for this run (max {limit}).")
                return f"Web search limit reached for this run (max {limit})."

            with self._run_lock:
                max_results_cap = int(self._run_budget.get("max_results_cap", self._default_max_results))
            max_results = min(int(max_results), int(max_results_cap))
            return self.search_as_string(
                query,
                max_results,
                topic,
                time_range,
                search_depth=search_depth,
            )

        return StructuredTool.from_function(
            name="web_search",
            description=(
                "Search the web for current information. "
                "Use this when you need up-to-date information, news, facts, or data not in your training. "
                "Supports basic or advanced depth based on the search_depth parameter. "
                "Returns formatted results with titles, URLs, and content snippets."
            ),
            func=_run_search,
            args_schema=SearchInput,
        )

web_search_tool = WebSearchTool()