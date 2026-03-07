"""
Retrieval Worker - Searches internal knowledge base.

The Retrieval Worker specializes in searching and retrieving
information from the vector database (Qdrant) containing
internal documents and knowledge.

Responsibilities:
- Search the vector store for relevant documents
- Apply hybrid search (dense + sparse vectors)
- Rerank and format results
- Provide source citations
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from workflows.state import (
    AgentState,
    WorkerResult,
    WorkerType,
)
from workflows.workers.base import BaseWorker
from infrastructure.tools.qdrant_tool import get_vector_db_tool
from infrastructure.rag.extra_tool import hyde_search, rewrite_search
from utils.log import log_info, log_debug, log_warning


RETRIEVAL_SYSTEM_PROMPT = """I am the Retrieval module. I search through Sensei's internal documents and knowledge bases to find the most relevant information.

Guidelines:
- I use the provided search results to build an accurate answer.
- I always cite sources (document name, section, page number if available).
- If the search results don't contain relevant information, I say so clearly — I don't invent facts.
- I synthesize information from multiple sources when appropriate.
- I present findings in a clean, organized format.

Output Format:
I present the relevant information clearly, with source citations in [brackets].
"""


class RetrievalWorker(BaseWorker):
    """
    Retrieval Worker searches the internal knowledge base.
    
    Uses hybrid search (dense + sparse vectors) with reranking
    to find the most relevant documents for the user's question.
    """
    
    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.RETRIEVAL
    
    @property
    def name(self) -> str:
        return "Retrieval Worker"
    
    @property
    def description(self) -> str:
        return "Searches internal documents and knowledge base for relevant information"
    
    @property
    def system_prompt(self) -> str:
        return RETRIEVAL_SYSTEM_PROMPT
    
    def __init__(self, config=None, top_k: int = 5):
        """
        Initialize the Retrieval Worker.
        
        Args:
            config: Optional agent configuration
            top_k: Number of documents to retrieve
        """
        super().__init__(config=config)
        self.top_k = top_k
        if config and hasattr(config, "top_k"):
            self.top_k = config.top_k
    
    def _execute(self, state: AgentState) -> WorkerResult:
        """
        Search the knowledge base and return relevant documents.
        
        Args:
            state: Current agent state
        
        Returns:
            WorkerResult containing search results
        """
        question = self.get_question(state)
        
        # Check if there's a specific query from the supervisor
        last_reasoning = self.get_last_decision_reasoning(state)
        search_query = self._extract_search_query(question, last_reasoning)
        
        log_info(f"Searching knowledge base for: {search_query[:100]}...")
        
        # Determine retrieval strategy from config
        strategy = "standard"
        if self.config and hasattr(self.config, "retrieval_strategy"):
            strategy = self.config.retrieval_strategy or "standard"

        # Extract user_id from state for tenant-scoped search
        user_id = state.get("user_id")

        # Check if user provided custom Cohere API key for reranking
        user_api_keys = state.get("metadata", {}).get("user_api_keys", {})
        user_cohere_key = user_api_keys.get("cohere") if user_api_keys else None

        # Set user's Cohere key on the rerank service if available
        if user_cohere_key:
            log_info("Using user's Cohere API key for reranking")
            vector_db = get_vector_db_tool()
            if hasattr(vector_db, "_rerank_service") and vector_db._rerank_service:
                vector_db._rerank_service.set_user_api_key(user_cohere_key)

        try:
            # Route to the appropriate search strategy
            if strategy == "hyde":
                log_info("Using HyDE retrieval strategy")
                results = hyde_search(question=search_query, k=self.top_k, user_id=user_id)
            elif strategy == "rewrite":
                log_info("Using query-rewrite retrieval strategy")
                results = rewrite_search(question=search_query, k=self.top_k, user_id=user_id)
            else:
                results = get_vector_db_tool().search_documents(
                    query=search_query,
                    k=self.top_k,
                    user_id=user_id,
                )
            
            if not results or results == "No relevant documents found in the knowledge base.":
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=True,
                    content="No relevant documents found in the knowledge base for this query.",
                    metadata={
                        "query": search_query,
                        "num_results": 0,
                    },
                )
            
            # Parse and format results
            formatted_results = self._format_results(results)
            num_results = results.count("### Result")
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=formatted_results,
                metadata={
                    "query": search_query,
                    "num_results": num_results,
                    "raw_results": results,
                },
            )
            
        except Exception as e:
            log_warning(f"Retrieval search failed: {e}")
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=str(e),
                metadata={"query": search_query},
            )
    
    def _extract_search_query(self, question: str, reasoning: str) -> str:
        """
        Extract or refine the search query.
        
        The supervisor may provide specific search instructions in its reasoning.
        Otherwise, use the original question.
        
        Args:
            question: Original user question
            reasoning: Supervisor's reasoning (may contain search hints)
        
        Returns:
            Search query to use
        """
        # Check if supervisor provided specific search terms
        if reasoning:
            # Look for explicit search instructions
            lower_reasoning = reasoning.lower()
            if "search for" in lower_reasoning:
                # Extract the search term after "search for"
                idx = lower_reasoning.find("search for")
                potential_query = reasoning[idx + 10:].strip()
                # Take until the end or a period
                if "." in potential_query:
                    potential_query = potential_query.split(".")[0]
                if potential_query:
                    return potential_query
        
        return question
    
    def _format_results(self, results: str) -> str:
        """
        Format the raw search results for presentation.
        
        Args:
            results: Raw results from vector_db_tool
        
        Returns:
            Formatted results string
        """
        # The results from vector_db_tool are already well-formatted
        # Just add a header
        header = "## Retrieved Information from Knowledge Base\n\n"
        return header + results
    
    def synthesize_with_llm(self, state: AgentState) -> WorkerResult:
        """
        Use LLM to synthesize retrieved information into a coherent answer.
        
        This is an optional method that can be called by the supervisor
        when more sophisticated synthesis is needed.
        
        Args:
            state: Current agent state with retrieval results
        
        Returns:
            WorkerResult with synthesized answer
        """
        question = self.get_question(state)
        context = self.get_context(state)
        
        if not context:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="No context available for synthesis",
            )
        
        prompt = f"""Based on the retrieved information, answer the following question.

Question: {question}

Retrieved Information:
{context}

Provide a clear, well-structured answer based ONLY on the retrieved information.
If the information is insufficient, say so clearly.
"""
        
        try:
            answer = self._call_llm(user_prompt=prompt)
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=answer,
                metadata={"synthesized": True},
            )
        except Exception as e:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=str(e),
            )
