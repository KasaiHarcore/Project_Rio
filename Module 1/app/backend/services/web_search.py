import os
import time
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timedelta
from functools import lru_cache

from langchain_tavily import TavilySearchAPIWrapper
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

from app.backend.utils.log import log_success, log_error, log_info, log_warning


class WebSearchTool:
    DEFAULT_MAX_RESULTS = 5
    DEFAULT_TOPIC = "general"
    CACHE_SIZE = 128
    CACHE_TTL = 3600  # 1 hour in seconds
    
    VALID_TOPICS = {"general", "news"}
    VALID_TIME_RANGES = {"day", "week", "month", "year"}
    
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
        
        self._search_wrapper: Optional[TavilySearchAPIWrapper] = None
        self._last_search_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
        
        log_info(f"WebSearchTool initialized (depth={search_depth}, max_results={max_results})")
    
    @property
    def search_wrapper(self) -> TavilySearchAPIWrapper:
        """Lazy-load Tavily search wrapper"""
        if self._search_wrapper is None:
            try:
                log_info("Initializing Tavily search wrapper...")
                self._search_wrapper = TavilySearchAPIWrapper(
                    tavily_api_key=self.api_key,
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
        include_answer: bool = True,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform web search with comprehensive options
        """
        max_results = max_results or self.max_results
        
        # Validate parameters
        query, max_results, topic, time_range = self._validate_params(
            query, max_results, topic, time_range
        )
        
        log_info(f"Searching: '{query}' (max={max_results}, topic={topic}, time={time_range})")
        
        try:
            self._rate_limit()
            
            # Build search kwargs
            search_kwargs = {
                "query": query,
                "max_results": max_results,
                "topic": topic,
                "include_answer": include_answer
            }
            
            if time_range:
                search_kwargs["days"] = self._time_range_to_days(time_range)
            
            if include_domains:
                search_kwargs["include_domains"] = include_domains
            
            if exclude_domains:
                search_kwargs["exclude_domains"] = exclude_domains
            
            # Perform search
            results = self.search_wrapper.results(**search_kwargs)
            
            # Format results
            formatted = self._format_results(results, query)
            
            log_success(f"Search completed: {len(formatted.get('results', []))} results found")
            return formatted
            
        except Exception as e:
            log_error(f"Search failed for '{query}': {e}")
            return {
                "query": query,
                "status": "error",
                "error": str(e),
                "results": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def _time_range_to_days(self, time_range: str) -> int:
        """Convert time range string to number of days"""
        mapping = {
            "day": 1,
            "week": 7,
            "month": 30,
            "year": 365
        }
        return mapping.get(time_range, 7)
    
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
        time_range: Optional[str] = None
    ) -> str:
        """
        Perform search and return formatted string (for agent tools)
        """
        result = self.search(query, max_results, topic, time_range)
        
        if result["status"] == "error":
            return f"Search failed: {result.get('error', 'Unknown error')}"
        
        # Build formatted string
        parts = [f"Search results for: '{query}'\n"]
        
        # Add answer if available
        if "answer" in result:
            parts.append(f"\n📌 Quick Answer:\n{result['answer']}\n")
        
        # Add results
        parts.append("\n🔍 Top Results:\n")
        for res in result["results"]:
            parts.append(
                f"\n[{res['rank']}] {res['title']}\n"
                f"URL: {res['url']}\n"
                f"{res['content'][:300]}{'...' if len(res['content']) > 300 else ''}\n"
            )
            if "score" in res:
                parts.append(f"Relevance: {res['score']:.2f}\n")
        
        return "".join(parts)
    
    def news_search(
        self,
        query: str,
        max_results: Optional[int] = None,
        time_range: str = "week"
    ) -> Dict[str, Any]:
        """
        Perform news-specific search
        """
        log_info(f"News search: '{query}'")
        return self.search(
            query=query,
            max_results=max_results,
            topic="news",
            time_range=time_range,
            include_answer=True
        )
    
    def quick_search(self, query: str, max_results: int = 3) -> str:
        """
        Quick search with minimal results (for fast lookups)
        """
        log_info(f"Quick search: '{query}'")
        return self.search_as_string(query, max_results=max_results)
    
    def deep_search(
        self,
        query: str,
        max_results: int = 10,
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deep search with more results and advanced depth
        """
        log_info(f"Deep search: '{query}'")
        
        # Temporarily switch to advanced depth if configured as basic
        original_depth = self.search_depth
        if self.search_depth == "basic":
            self.search_wrapper._search_depth = "advanced"
        
        try:
            results = self.search(
                query=query,
                max_results=max_results,
                time_range=time_range,
                include_answer=True
            )
            return results
        finally:
            # Restore original depth
            if original_depth == "basic":
                self.search_wrapper._search_depth = "basic"
    
    def get_search_tool(self) -> StructuredTool:
        """
        Get LangChain StructuredTool for agent integration
        """
        class SearchInput(BaseModel):
            query: str = Field(..., description="The search query")
            max_results: int = Field(default=5, description="Number of results (1-20)")
            topic: str = Field(default="general", description="Search topic: 'general' or 'news'")
            time_range: Optional[str] = Field(default=None, description="Time filter: 'day', 'week', 'month', or 'year'")
        
        return StructuredTool.from_function(
            name="web_search",
            description=(
                "Search the web for current information. "
                "Use this when you need up-to-date information, news, facts, or data not in your training. "
                "Returns formatted results with titles, URLs, and content snippets."
            ),
            func=lambda query, max_results=5, topic="general", time_range=None: 
                self.search_as_string(query, max_results, topic, time_range),
            args_schema=SearchInput
        )


# Global instance
web_search_tool = WebSearchTool()