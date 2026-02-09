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

from application.workflows.state import (
    AgentState,
    WorkerResult,
    WorkerType,
)
from application.workflows.workers.base import BaseWorker
from infrastructure.integrations.tools.qdrant_tool import vector_db_tool
from utils.log import log_info, log_debug, log_warning


RETRIEVAL_SYSTEM_PROMPT = """You are a Retrieval Assistant that searches internal documents and knowledge bases.

Your role is to find and present relevant information from the document store.

Guidelines:
- Use the provided search results to answer questions
- Always cite your sources (document name, page number if available)
- If the search results don't contain relevant information, say so clearly
- Synthesize information from multiple sources when appropriate
- Focus on accuracy - don't make up information not in the sources

Output Format:
Present the relevant information clearly, with source citations in [brackets].
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
        
        try:
            # Perform the search
            results = vector_db_tool.search_documents(
                query=search_query,
                k=self.top_k,
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


def create_retrieval_worker(config=None, top_k: int = 5) -> RetrievalWorker:
    """Factory function to create a RetrievalWorker."""
    return RetrievalWorker(config=config, top_k=top_k)
