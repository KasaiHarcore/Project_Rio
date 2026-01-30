"""
Advanced Retrieval Tools
- HyDE: Generates hypothetical documents for semantic search
- Query Rewriting/Normalization: Rewrites queries into a retrieval-optimized form
"""
import json

from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.services.llm import form
from backend.core.settings import AgentConfig
from backend.services.tools.qdrant_tool import vector_db_tool
from backend.utils.log import log_info, log_success, log_error, log_warning


class HypotheticalDocuments(BaseModel):
    """Structured output for multiple hypothetical documents"""
    hypothesis_1: str = Field(..., description="First hypothetical document from one perspective")
    hypothesis_2: str = Field(..., description="Second hypothetical document from different angle")
    hypothesis_3: str = Field(..., description="Third hypothetical document from another perspective")


class NormalizedQuery(BaseModel):
    """Structured output for query rewriting/normalization."""

    query: str = Field(
        ..., description="A rewritten/normalized query string optimized for retrieving relevant documents"
    )


class HyDETool: 
    """
    HyDE (Hypothetical Document Embeddings) retrieval tool
    """

    HYDE_SYSTEM_PROMPT = """You are an expert document generator. Given a user query, generate 3 DIFFERENT hypothetical answers/documents that would answer the query from different angles or perspectives.

Key Guidelines for EACH hypothesis:
- Approach the answer from a different perspective or cover different aspects
- Write as if you have access to the exact information needed
- Use professional, factual language typical of policy documents
- Keep each document concise (1-2 paragraphs)
- DO NOT add disclaimers or uncertainty - write as fact

You MUST respond with ONLY valid JSON in this EXACT format:
{
  "hypothesis_1": "First perspective (e.g., main policy overview)",
  "hypothesis_2": "Second perspective (e.g., procedural details)",
  "hypothesis_3": "Third perspective (e.g., exceptions or edge cases)"
}

DO NOT include any text before or after the JSON. ONLY JSON."""

    @staticmethod
    def generate_hypothetical_documents(
        question: str,
        config: Optional[AgentConfig] = None,
    ) -> List[str]:
        """
        Generate 3 different hypothetical documents using structured output
        """
        # Use default config if not provided
        if config is None:
            config = AgentConfig()

        # Set model if specified
        if config.model_name:
            form.set_model(config.model_name)

        # Validate model is set
        if not form.SELECTED_MODEL:
            raise ValueError("No model is registered. Check backend.services.llm.form configuration.")

        # Ensure model is initialized
        if not hasattr(form.SELECTED_MODEL, "llm") or not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()

        log_info(f"Generating 3 hypothetical documents for: '{question}'")

        # Generate hypothetical documents - FORCE JSON OUTPUT
        messages = [
            SystemMessage(content=HyDETool.HYDE_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        response = form.SELECTED_MODEL.llm.invoke(messages)
        content = response.content.strip() if hasattr(response, "content") else str(response).strip()

        try:
            # Extract JSON if wrapped in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON
            json_data = json.loads(content)

            # Validate with Pydantic
            result = HypotheticalDocuments(**json_data)

            # Extract the 3 hypotheses
            hypotheses = [
                result.hypothesis_1.strip(),
                result.hypothesis_2.strip(),
                result.hypothesis_3.strip(),
            ]

            # Validate all are non-empty
            if not all(hypotheses):
                raise ValueError(f"One or more hypotheses are empty: {hypotheses}")

            log_success(
                f"Generated 3 hypothetical documents (avg {sum(len(h) for h in hypotheses)//3} chars each)"
            )
            for i, h in enumerate(hypotheses, 1):
                log_info(f"  Hypothesis {i}: {h[:80]}...")

            return hypotheses

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON from LLM: {e}"
            log_error(error_msg)
            raise ValueError(f"LLM must return valid JSON. Got: {content[:200]}") from e

        except Exception as e:
            error_msg = f"Failed to generate hypothetical documents: {e}"
            log_error(error_msg)
            raise

    @staticmethod
    def hyde_search(
        question: str,
        k: int = 10,
        config: Optional[AgentConfig] = None,
    ) -> str:
        """
        Perform HyDE-enhanced search using multiple hypothetical documents
        """
        if not question or not question.strip():
            log_warning("Empty query provided to hyde_search")
            return "No query provided."

        log_info(f"Multi-HyDE search initiated: query='{question}', target k={k}")

        try:
            # Generate 3 hypothetical documents
            hypotheses = HyDETool.generate_hypothetical_documents(question, config)

            # Search separately with each hypothesis
            # Request more results per hypothesis to ensure good coverage after deduplication
            k_per_hypothesis = max(k // 2, 5)  # At least 5 results per hypothesis

            all_results = []
            seen_contents = {}  # Track unique content by first 100 chars

            for i, hypo_doc in enumerate(hypotheses, 1):
                log_info(f"Searching with hypothesis {i}/3...")

                results_str = vector_db_tool.search_documents(hypo_doc, k=k_per_hypothesis)

                # Parse results to deduplicate
                # Simple deduplication: track by content snippet
                if results_str and results_str != "No query provided.":
                    # Split by result markers
                    result_blocks = results_str.split("[Result ")

                    for block in result_blocks:
                        if not block.strip():
                            continue

                        # Extract content (rough approach - get first 100 chars of actual content)
                        lines = block.split("\n")
                        if len(lines) > 1:
                            # Content usually starts after the header line
                            content_snippet = "".join(lines[1:])[:100].strip()

                            if content_snippet and content_snippet not in seen_contents:
                                seen_contents[content_snippet] = "[Result " + block
                                all_results.append("[Result " + block)

            # Take top-K results
            final_results = all_results[:k]

            if not final_results:
                log_warning("No results found across all hypotheses")
                return "No relevant documents found in the knowledge base."

            # Combine results
            combined = "\n\n" + "=" * 60 + "\n\n".join([""] + final_results)

            log_success(
                f"Multi-HyDE search completed: {len(final_results)} unique results from 3 hypotheses"
            )
            return combined

        except Exception as e:
            error_msg = f"Multi-HyDE search failed: {e}"
            log_error(error_msg)
            # Fallback to regular search
            log_warning("Falling back to standard search")
            return vector_db_tool.search_documents(question, k=k)

    def get_hyde_retriever_tool(
        self,
        *,
        default_k: int = 5,
        config: Optional[AgentConfig] = None,
    ) -> "StructuredTool":
        """Get LangChain StructuredTool for HyDE retrieval."""
        from langchain_core.tools import StructuredTool

        class HyDERetrieverInput(BaseModel):
            query: str = Field(..., description="Search query for policy documents")
            k: int = Field(default=default_k, description="Number of results to retrieve")

        def _run_hyde(query: str, k: int = default_k) -> str:
            return HyDETool.hyde_search(query, k=k, config=config)

        return StructuredTool.from_function(
            name="hyde_retriever",
            description=(
                "HyDE (Hypothetical Document Embeddings) search. "
                "Generates a complete hypothetical answer first, then searches for similar documents. "
            ),
            func=_run_hyde,
            args_schema=HyDERetrieverInput,
        )

hyde_tool = HyDETool()


class QueryRewriteTool:
    """LLM-based query rewriting/normalization.

    Produces a single retrieval-optimized query string and is intended to be fed
    directly into the vector search tool.
    """

    REWRITE_SYSTEM_PROMPT = """You are an expert search query normalizer for an internal policy knowledge base.

Your job: rewrite the user's input into ONE concise, retrieval-optimized query.

Rules:
- Output must be ONLY valid JSON (no markdown, no extra text).
- JSON format MUST be exactly: {"query": "..."}
- Keep the original language (Vietnamese stays Vietnamese; English stays English).
- Remove filler/chitchat, keep intent + key entities.
- Prefer explicit policy/HR terms and concrete keywords.
- Preserve codes/IDs exactly if present (e.g., FPT-HR-01).
- Do NOT answer the question; only rewrite the query.

Return ONLY JSON."""

    @staticmethod
    def rewrite_query(question: str, config: Optional[AgentConfig] = None) -> str:
        if not question or not question.strip():
            log_warning("Empty query provided to rewrite_query")
            return ""

        if config is None:
            config = AgentConfig()

        if config.model_name:
            form.set_model(config.model_name)

        if not form.SELECTED_MODEL:
            raise ValueError("No model is registered. Check backend.services.llm.form configuration.")

        if not hasattr(form.SELECTED_MODEL, "llm") or not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()

        log_info(f"Rewriting/normalizing query: '{question}'")

        messages = [
            SystemMessage(content=QueryRewriteTool.REWRITE_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        response = form.SELECTED_MODEL.llm.invoke(messages)
        content = response.content.strip() if hasattr(response, "content") else str(response).strip()

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            json_data = json.loads(content)
            result = NormalizedQuery(**json_data)
            normalized = result.query.strip()

            if not normalized:
                raise ValueError("Normalized query is empty")

            log_success(f"Normalized query generated ({len(normalized)} chars)")
            log_info(f"  Normalized: {normalized[:120]}...")
            return normalized

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON from LLM: {e}"
            log_error(error_msg)
            raise ValueError(f"LLM must return valid JSON. Got: {content[:200]}") from e
        except Exception as e:
            error_msg = f"Failed to rewrite/normalize query: {e}"
            log_error(error_msg)
            raise


class RewriteRetrieverTool:
    """Retrieval tool that normalizes the query first, then runs vector search."""

    @staticmethod
    def rewrite_search(question: str, k: int = 10, config: Optional[AgentConfig] = None) -> str:
        if not question or not question.strip():
            log_warning("Empty query provided to rewrite_search")
            return "No query provided."

        log_info(f"Rewrite retrieval initiated: query='{question}', k={k}")

        try:
            normalized = QueryRewriteTool.rewrite_query(question, config=config)
            # If rewrite returned empty for any reason, fallback.
            if not normalized:
                log_warning("Query rewrite returned empty; falling back to standard search")
                return vector_db_tool.search_documents(question, k=k)

            return vector_db_tool.search_documents(normalized, k=k)

        except Exception as e:
            log_warning(f"Rewrite retrieval failed; falling back to standard search: {e}")
            return vector_db_tool.search_documents(question, k=k)

    def get_rewrite_retriever_tool(
        self,
        *,
        default_k: int = 5,
        config: Optional[AgentConfig] = None,
    ) -> "StructuredTool":
        """Get LangChain StructuredTool for rewrite retrieval (query rewrite + search)."""
        from langchain_core.tools import StructuredTool

        class RewriteRetrieverInput(BaseModel):
            query: str = Field(..., description="User query to rewrite/normalize before searching")
            k: int = Field(default=default_k, description="Number of results to retrieve")

        def _run_rewrite(query: str, k: int = default_k) -> str:
            return RewriteRetrieverTool.rewrite_search(query, k=k, config=config)

        return StructuredTool.from_function(
            name="rewrite_retriever",
            description=(
                "Retrieval that first rewrites/normalizes the query using the LLM, "
                "then runs standard hybrid search (dense + sparse). "
            ),
            func=_run_rewrite,
            args_schema=RewriteRetrieverInput,
        )


rewrite_retriever_tool = RewriteRetrieverTool()
