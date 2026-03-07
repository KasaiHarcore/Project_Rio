"""
Web Search Worker - Searches the internet for current information.

The Web Search Worker specializes in finding information from
the web using the Tavily search API.

Responsibilities:
- Search the web for current information
- Filter and validate search results
- Handle rate limiting and budgets
- Format results with source citations
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from workflows.state import (
    AgentState,
    WorkerResult,
    WorkerType,
)
from workflows.workers.base import BaseWorker
from core.exceptions import ExternalServiceError
from infrastructure.tools.web_search_tool import web_search_tool, WebSearchTool
from utils.log import log_info, log_debug, log_warning


WEB_SEARCH_SYSTEM_PROMPT = """I am the Web Search module. I find current, up-to-date information from the internet for Sensei.

Guidelines:
- I always cite sources with URLs.
- I prioritize authoritative sources (official sites, reputable publications).
- I note publication dates for time-sensitive information.
- If search results are inconclusive or conflicting, I say so.
- I cross-reference information when possible for accuracy.

Output Format:
I present findings with clear source attribution:
- [Source Name](URL): Key information found
"""


class WebSearchWorker(BaseWorker):
    """
    Web Search Worker searches the internet for information.
    
    Uses Tavily search API with rate limiting and budget controls
    to find current, relevant information from the web.
    """
    
    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.WEB_SEARCH
    
    @property
    def name(self) -> str:
        return "Web Search Worker"
    
    @property
    def description(self) -> str:
        return "Searches the web for current information, news, and facts"
    
    @property
    def system_prompt(self) -> str:
        return WEB_SEARCH_SYSTEM_PROMPT
    
    def __init__(
        self,
        config=None,
        max_results: int = 5,
        search_depth: str = "basic",
    ):
        """
        Initialize the Web Search Worker.
        
        Args:
            config: Optional agent configuration
            max_results: Maximum search results to return
            search_depth: Search depth ("basic" or "advanced")
        """
        super().__init__(config=config)
        self.max_results = max_results
        self.search_depth = search_depth
        
        # Configure from agent config if available
        if config:
            if hasattr(config, "web_search_max_results"):
                self.max_results = config.web_search_max_results
    
    def _execute(self, state: AgentState) -> WorkerResult:
        """
        Search the web and return relevant results.
        
        Args:
            state: Current agent state
        
        Returns:
            WorkerResult containing search results
        """
        question = self.get_question(state)

        # Extract search query from question or supervisor reasoning
        last_reasoning = self.get_last_decision_reasoning(state)
        search_queries = self._extract_search_queries(question, last_reasoning)

        log_info(f"Web search for: {search_queries}")

        # Check if user provided custom Tavily API key
        user_api_keys = state.get("metadata", {}).get("user_api_keys", {})
        user_tavily_key = user_api_keys.get("tavily") if user_api_keys else None

        # Use user's Tavily key if available, otherwise use global instance
        if user_tavily_key:
            log_info("Using user's Tavily API key")
            search_tool = WebSearchTool(
                api_key=user_tavily_key,
                max_results=self.max_results,
                search_depth=self.search_depth,
            )
        else:
            search_tool = web_search_tool

        # Configure the search tool for this run
        if self.config:
            search_tool.configure_run(
                max_calls=getattr(self.config, "web_search_max_calls", 6),
                max_results=self.max_results,
                dedupe=getattr(self.config, "web_search_dedupe", True),
            )
        
        all_results: List[Dict[str, Any]] = []
        errors: List[str] = []
        
        # Execute searches
        for query in search_queries[:3]:  # Limit to 3 queries
            try:
                result = search_tool.search(
                    query=query,
                    max_results=self.max_results,
                    search_depth=self.search_depth,
                )
                
                if result.get("status") == "success":
                    all_results.append({
                        "query": query,
                        "results": result.get("results", []),
                        "answer": result.get("answer"),
                    })
                else:
                    errors.append(f"Query '{query}': {result.get('error', 'No results')}")
                    
            except ExternalServiceError:
                raise
            except Exception as e:
                errors.append(f"Query '{query}': {str(e)}")
                log_warning(f"Web search failed for '{query}': {e}")

        # Format results
        if all_results:
            formatted = self._format_results(all_results)
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=formatted,
                metadata={
                    "queries": search_queries,
                    "num_results": sum(len(r["results"]) for r in all_results),
                    "errors": errors if errors else None,
                },
            )
        
        # No results
        error_msg = "; ".join(errors) if errors else "No results found"
        return WorkerResult(
            worker_type=self.worker_type,
            success=False,
            content=f"Web search did not return useful results. {error_msg}",
            error=error_msg,
            metadata={"queries": search_queries},
        )
    
    def _extract_search_queries(
        self,
        question: str,
        reasoning: str,
    ) -> List[str]:
        """
        Extract one or more search queries from the question and reasoning.
        
        Args:
            question: Original user question
            reasoning: Supervisor's reasoning
        
        Returns:
            List of search queries
        """
        queries = []
        
        # Check if supervisor provided specific search terms
        if reasoning:
            lower_reasoning = reasoning.lower()
            
            # Look for explicit search instructions
            search_markers = ["search for", "look up", "find information about"]
            for marker in search_markers:
                if marker in lower_reasoning:
                    idx = lower_reasoning.find(marker)
                    potential_query = reasoning[idx + len(marker):].strip()
                    # Take until period or newline
                    for delim in [".", "\n", ","]:
                        if delim in potential_query:
                            potential_query = potential_query.split(delim)[0]
                    if potential_query and len(potential_query) > 3:
                        queries.append(potential_query.strip())
        
        # Always include the original question if no specific queries
        if not queries:
            queries.append(question)
        
        return queries
    
    def _format_results(self, all_results: List[Dict[str, Any]]) -> str:
        """
        Format search results for presentation.
        
        Args:
            all_results: List of search result dictionaries
        
        Returns:
            Formatted results string
        """
        parts = ["## Web Search Results\n"]
        
        for search in all_results:
            query = search["query"]
            results = search["results"]
            answer = search.get("answer")
            
            parts.append(f"\n### Query: {query}\n")
            
            # Add quick answer if available
            if answer:
                parts.append(f"**Quick Answer:** {answer}\n")
            
            # Add individual results
            if results:
                parts.append("\n**Sources:**\n")
                for idx, result in enumerate(results, 1):
                    title = result.get("title", "Untitled")
                    url = result.get("url", "")
                    content = result.get("content", "")[:300]
                    score = result.get("score", 0)
                    
                    parts.append(f"\n**[{idx}] {title}**")
                    if url:
                        parts.append(f"\nURL: {url}")
                    if content:
                        parts.append(f"\n{content}...")
                    if score:
                        parts.append(f"\n*Relevance: {score:.2f}*")
                    parts.append("\n")
        
        return "\n".join(parts)
    
    def search_specific(
        self,
        query: str,
        topic: str = "general",
        time_range: Optional[str] = None,
    ) -> WorkerResult:
        """
        Perform a specific web search with custom parameters.
        
        Args:
            query: Search query
            topic: Search topic ("general" or "news")
            time_range: Time filter ("day", "week", "month", "year")
        
        Returns:
            WorkerResult with search results
        """
        try:
            result = web_search_tool.search(
                query=query,
                max_results=self.max_results,
                topic=topic,
                time_range=time_range,
                search_depth=self.search_depth,
            )
            
            if result.get("status") == "success":
                formatted = self._format_results([{
                    "query": query,
                    "results": result.get("results", []),
                    "answer": result.get("answer"),
                }])
                
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=True,
                    content=formatted,
                    metadata={
                        "query": query,
                        "topic": topic,
                        "time_range": time_range,
                    },
                )
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="Search did not return results",
                error=result.get("error", "Unknown error"),
            )
            
        except Exception as e:
            raise ExternalServiceError(
                f"Web search failed: {e}",
                details={"query": query, "topic": topic},
            )
