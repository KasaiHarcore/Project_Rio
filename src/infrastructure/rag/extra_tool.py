"""Advanced retrieval strategies for the RAG pipeline.

- HyDE: Generates hypothetical documents for semantic search (improves recall).
- Query Rewrite: Normalizes queries into retrieval-optimized form (improves precision).
- Rewrite + Search: Pipeline combining both.

All functions are stateless utilities called by RetrievalWorker based on
``AgentConfig.retrieval_strategy``.
"""

import json
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from infrastructure.llm import form
from infrastructure.tools.qdrant_tool import get_vector_db_tool
from utils.log import log_info, log_success, log_error, log_warning


# ── Pydantic schemas for structured LLM output ────────────────────────────

class HypotheticalDocuments(BaseModel):
    """Structured output for multiple hypothetical documents."""
    hypothesis_1: str = Field(..., description="First hypothetical document from one perspective")
    hypothesis_2: str = Field(..., description="Second hypothetical document from different angle")
    hypothesis_3: str = Field(..., description="Third hypothetical document from another perspective")


class NormalizedQuery(BaseModel):
    """Structured output for query rewriting/normalization."""
    query: str = Field(
        ..., description="A rewritten/normalized query string optimized for retrieving relevant documents"
    )


# ── Internal helpers ───────────────────────────────────────────────────────

def _get_llm():
    """Return the active LLM instance, ensuring it's ready."""
    if not form.SELECTED_MODEL:
        raise RuntimeError("No model is registered. Check llm.form configuration.")
    if not getattr(form.SELECTED_MODEL, "llm", None):
        form.SELECTED_MODEL.setup()
    return form.SELECTED_MODEL.llm


def _parse_json_response(content: str) -> dict:
    """Extract and parse JSON from an LLM response (handles markdown fences)."""
    text = content.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


# ── HyDE ───────────────────────────────────────────────────────────────────

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


def generate_hypothetical_documents(question: str) -> List[str]:
    """Generate 3 hypothetical documents for HyDE retrieval.

    Returns:
        List of 3 hypothesis strings.

    Raises:
        ValueError: If LLM returns invalid/unparseable JSON.
    """
    llm = _get_llm()

    log_info(f"Generating 3 hypothetical documents for: '{question}'")

    response = llm.invoke([
        SystemMessage(content=HYDE_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ])
    content = response.content.strip() if hasattr(response, "content") else str(response).strip()

    try:
        json_data = _parse_json_response(content)
        result = HypotheticalDocuments(**json_data)
        hypotheses = [
            result.hypothesis_1.strip(),
            result.hypothesis_2.strip(),
            result.hypothesis_3.strip(),
        ]
        if not all(hypotheses):
            raise ValueError(f"One or more hypotheses are empty: {hypotheses}")

        log_success(
            f"Generated 3 hypothetical documents (avg {sum(len(h) for h in hypotheses) // 3} chars each)"
        )
        return hypotheses

    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON from LLM: {e}")
        raise ValueError(f"LLM must return valid JSON. Got: {content[:200]}") from e
    except Exception as e:
        log_error(f"Failed to generate hypothetical documents: {e}")
        raise


def hyde_search(question: str, k: int = 10, *, user_id: Optional[str] = None) -> str:
    """Perform HyDE-enhanced search: generate hypothetical docs, search with each, deduplicate.

    Falls back to standard search on failure.
    """
    if not question or not question.strip():
        log_warning("Empty query provided to hyde_search")
        return "No query provided."

    log_info(f"HyDE search initiated: query='{question}', target k={k}, user_id={user_id or 'all'}")

    try:
        hypotheses = generate_hypothetical_documents(question)

        k_per_hypothesis = max(k // 2, 5)
        all_results: List[str] = []
        seen_contents: dict[str, str] = {}

        for i, hypo_doc in enumerate(hypotheses, 1):
            log_info(f"Searching with hypothesis {i}/3...")
            results_str = get_vector_db_tool().search_documents(hypo_doc, k=k_per_hypothesis, user_id=user_id)

            if results_str and results_str != "No query provided.":
                result_blocks = results_str.split("### Result ")
                for block in result_blocks:
                    if not block.strip():
                        continue
                    lines = block.split("\n")
                    if len(lines) > 1:
                        content_snippet = "".join(lines[1:])[:100].strip()
                        if content_snippet and content_snippet not in seen_contents:
                            seen_contents[content_snippet] = "### Result " + block
                            all_results.append("### Result " + block)

        final_results = all_results[:k]

        if not final_results:
            log_warning("No results found across all hypotheses")
            return "No relevant documents found in the knowledge base."

        combined = "\n\n---\n\n".join(final_results)
        log_success(f"HyDE search completed: {len(final_results)} unique results from 3 hypotheses")
        return combined

    except Exception as e:
        log_error(f"HyDE search failed: {e}")
        log_warning("Falling back to standard search")
        return get_vector_db_tool().search_documents(question, k=k, user_id=user_id)


# ── Query Rewrite ──────────────────────────────────────────────────────────

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


def rewrite_query(question: str) -> str:
    """Rewrite/normalize a query for optimal retrieval.

    Returns:
        Normalized query string.

    Raises:
        ValueError: If LLM returns invalid JSON or empty query.
    """
    if not question or not question.strip():
        log_warning("Empty query provided to rewrite_query")
        return ""

    llm = _get_llm()
    log_info(f"Rewriting/normalizing query: '{question}'")

    response = llm.invoke([
        SystemMessage(content=REWRITE_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ])
    content = response.content.strip() if hasattr(response, "content") else str(response).strip()

    try:
        json_data = _parse_json_response(content)
        result = NormalizedQuery(**json_data)
        normalized = result.query.strip()

        if not normalized:
            raise ValueError("Normalized query is empty")

        log_success(f"Normalized query generated ({len(normalized)} chars)")
        log_info(f"  Normalized: {normalized[:120]}...")
        return normalized

    except json.JSONDecodeError as e:
        log_error(f"Failed to parse JSON from LLM: {e}")
        raise ValueError(f"LLM must return valid JSON. Got: {content[:200]}") from e
    except Exception as e:
        log_error(f"Failed to rewrite/normalize query: {e}")
        raise


def rewrite_search(question: str, k: int = 10, *, user_id: Optional[str] = None) -> str:
    """Rewrite query then perform standard vector search.

    Falls back to standard search if rewrite fails.
    """
    if not question or not question.strip():
        log_warning("Empty query provided to rewrite_search")
        return "No query provided."

    log_info(f"Rewrite retrieval initiated: query='{question}', k={k}, user_id={user_id or 'all'}")

    try:
        normalized = rewrite_query(question)
        if not normalized:
            log_warning("Query rewrite returned empty; falling back to standard search")
            return get_vector_db_tool().search_documents(question, k=k, user_id=user_id)
        return get_vector_db_tool().search_documents(normalized, k=k, user_id=user_id)
    except Exception as e:
        log_warning(f"Rewrite retrieval failed; falling back to standard search: {e}")
        return get_vector_db_tool().search_documents(question, k=k, user_id=user_id)
