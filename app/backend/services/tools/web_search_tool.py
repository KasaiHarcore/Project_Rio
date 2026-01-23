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

class WebSearchTool:
    DEFAULT_MAX_RESULTS = 5
    DEFAULT_TOPIC = "general"
    CACHE_SIZE = 128
    CACHE_TTL = 3600  # 1 hour in seconds
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
        
        self._search_wrapper: Optional[TavilySearch] = None
        self._last_search_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_order: List[str] = []

        self._call_state = threading.local()
        self._default_call_limit = int(os.getenv("WEB_SEARCH_MAX_CALLS", "2"))
        
        log_info(f"WebSearchTool initialized (depth={search_depth}, max_results={max_results})")

    def reset_call_limit(self, max_calls: Optional[int] = None) -> None:
        """Reset per-run call limit counter for this tool."""
        limit = self._default_call_limit if max_calls is None else int(max_calls)
        setattr(self._call_state, "call_limit", max(0, limit))
        setattr(self._call_state, "call_count", 0)

    def _consume_call(self) -> bool:
        """Return True if another call is allowed, else False."""
        limit = getattr(self._call_state, "call_limit", self._default_call_limit)
        count = getattr(self._call_state, "call_count", 0)
        if limit <= 0:
            return False
        if count >= limit:
            return False
        setattr(self._call_state, "call_count", count + 1)
        return True

    def _get_cached(self, cache_key: str) -> Optional[Dict[str, Any]]:
        cached = self._cache.get(cache_key)
        if not cached:
            return None
        if time.time() - float(cached.get("timestamp", 0)) > self.CACHE_TTL:
            self._cache.pop(cache_key, None)
            if cache_key in self._cache_order:
                self._cache_order.remove(cache_key)
            return None
        return cached

    def _set_cached(self, cache_key: str, result: Dict[str, Any]) -> None:
        if cache_key in self._cache_order:
            self._cache_order.remove(cache_key)
        self._cache_order.append(cache_key)
        self._cache[cache_key] = {
            "timestamp": time.time(),
            "result": result,
        }
        while len(self._cache_order) > self.CACHE_SIZE:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)

    def _check_search_limit(self) -> None:
        """Enforce max searches within time window."""
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
        max_results = max_results or self.max_results
        effective_search_depth = search_depth or self.search_depth
        
        # Validate parameters
        query, max_results, topic, time_range = self._validate_params(
            query, max_results, topic, time_range
        )
        
        log_info(
            f"Searching: '{query}' (max={max_results}, topic={topic}, time={time_range}, depth={effective_search_depth})"
        )

        cache_key = f"{query}|{max_results}|{topic}|{time_range}|{effective_search_depth}"
        cached = self._get_cached(cache_key)
        
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

            self._set_cached(cache_key, formatted)
            
            log_success(f"Search completed: {len(formatted.get('results', []))} results found")
            return formatted

        except ValueError as e:
            if "Search limit reached" in str(e):
                if cached:
                    log_warning(f"Search limit reached, returning cached results for '{query}'")
                    cached_result = dict(cached.get("result", {}))
                    cached_result["cached"] = True
                    return cached_result
                log_warning(f"Search limit reached, no cached results for '{query}'")
            else:
                log_error(f"Search failed for '{query}': {e}")
        except Exception as e:
            log_error(f"Search failed for '{query}': {e}")

        if cached:
            log_warning(f"Search failed, returning cached results for '{query}'")
            cached_result = dict(cached.get("result", {}))
            cached_result["cached"] = True
            return cached_result

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
            if not self._consume_call():
                limit = getattr(self._call_state, "call_limit", self._default_call_limit)
                log_warning(f"Web search call limit reached for this run (max {limit}).")
                return f"Web search limit reached for this run (max {limit})."
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