"""
Advanced Retrieval Tools
- HyDE: Generates hypothetical documents for semantic search
- Query Expansion: Reformulates queries with better keywords
"""
import json

from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.backend.api import form
from app.backend.config import AgentConfig
from app.backend.services.qdrant import vector_db_tool
from app.backend.utils.log import log_info, log_success, log_error, log_warning


class HypotheticalDocuments(BaseModel):
    """Structured output for multiple hypothetical documents"""
    hypothesis_1: str = Field(..., description="First hypothetical document from one perspective")
    hypothesis_2: str = Field(..., description="Second hypothetical document from different angle")
    hypothesis_3: str = Field(..., description="Third hypothetical document from another perspective")


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
        config: Optional[AgentConfig] = None
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
            raise ValueError("No model is registered. Check app.backend.api.form configuration.")
        
        # Ensure model is initialized
        if not hasattr(form.SELECTED_MODEL, 'llm') or not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()
        
        log_info(f"Generating 3 hypothetical documents for: '{question}'")
        
        # Generate hypothetical documents - FORCE JSON OUTPUT
        messages = [
            SystemMessage(content=HyDETool.HYDE_SYSTEM_PROMPT),
            HumanMessage(content=question)
        ]
        
        response = form.SELECTED_MODEL.llm.invoke(messages)
        content = response.content.strip() if hasattr(response, 'content') else str(response).strip()

        try:
            # Extract JSON if wrapped in markdown code blocks
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            json_data = json.loads(content)
            
            # Validate with Pydantic
            result = HypotheticalDocuments(**json_data)
            
            # Extract the 3 hypotheses
            hypotheses = [
                result.hypothesis_1.strip(),
                result.hypothesis_2.strip(),
                result.hypothesis_3.strip()
            ]
            
            # Validate all are non-empty
            if not all(hypotheses):
                raise ValueError(f"One or more hypotheses are empty: {hypotheses}")
            
            log_success(f"Generated 3 hypothetical documents (avg {sum(len(h) for h in hypotheses)//3} chars each)")
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
        config: Optional[AgentConfig] = None
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
                        lines = block.split('\n')
                        if len(lines) > 1:
                            # Content usually starts after the header line
                            content_snippet = ''.join(lines[1:])[:100].strip()
                            
                            if content_snippet and content_snippet not in seen_contents:
                                seen_contents[content_snippet] = "[Result " + block
                                all_results.append("[Result " + block)
            
            # Take top-K results
            final_results = all_results[:k]
            
            if not final_results:
                log_warning("No results found across all hypotheses")
                return "No relevant documents found in the knowledge base."
            
            # Combine results
            combined = "\n\n" + "="*60 + "\n\n".join([""] + final_results)
            
            log_success(f"Multi-HyDE search completed: {len(final_results)} unique results from 3 hypotheses")
            return combined
            
        except Exception as e:
            error_msg = f"Multi-HyDE search failed: {e}"
            log_error(error_msg)
            # Fallback to regular search
            log_warning("Falling back to standard search")
            return vector_db_tool.search_documents(question, k=k)


class ExpandedQuery(BaseModel):
    """Structured output for expanded query"""
    expanded_query: str = Field(..., description="Expanded search query with relevant keywords, synonyms, and related terms")


class QueryExpansionTool:
    """
    Query Expansion retrieval tool
    """
    
    QUERY_EXPANSION_PROMPT = """You are a query expansion expert. Given a user's question, expand it into a better search query that will find relevant policy documents.

Key Guidelines:
- Add relevant keywords and terminology that might appear in policy documents
- Reformulate vague questions into specific search terms
- Include synonyms and related concepts
- Keep it concise (1-3 sentences max)
- Focus on SEARCHABLE terms, not a full answer
- Use professional/formal language typical of policies

Examples:
User: "vacation days"
Expanded: "vacation days paid time off PTO leave policy annual leave entitlement"

User: "How to handle conflicts?"
Expanded: "workplace conflict resolution procedures mediation dispute handling employee grievance process"

User: "remote work policy"
Expanded: "remote work policy telecommuting work from home WFH hybrid work arrangements"

You MUST respond with ONLY valid JSON in this EXACT format:
{
  "expanded_query": "your expanded query here"
}

DO NOT include any text before or after the JSON. ONLY JSON."""

    @staticmethod
    def expand_query(
        question: str,
        config: Optional[AgentConfig] = None
    ) -> str:
        """
        Expand and reformulate query using LLM with structured output
        """
        # Use default config if not provided
        if config is None:
            config = AgentConfig()
        
        # Set model if specified
        if config.model_name:
            form.set_model(config.model_name)
        
        # Validate model is set
        if not form.SELECTED_MODEL:
            raise ValueError("No model is registered. Check app.backend.api.form configuration.")
        
        # Ensure model is initialized
        if not hasattr(form.SELECTED_MODEL, 'llm') or not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()
        
        log_info(f"Expanding query: '{question}'")
        
        # Generate expanded query - FORCE JSON OUTPUT
        messages = [
            SystemMessage(content=QueryExpansionTool.QUERY_EXPANSION_PROMPT),
            HumanMessage(content=question)
        ]
        
        response = form.SELECTED_MODEL.llm.invoke(messages)
        content = response.content.strip() if hasattr(response, 'content') else str(response).strip()
        
        # Extract JSON if wrapped in markdown code blocks
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        # Parse JSON
        json_data = json.loads(content)
        
        # Validate with Pydantic
        result = ExpandedQuery(**json_data)
        expanded = result.expanded_query.strip()
        
        if not expanded:
            raise ValueError("LLM returned empty expanded_query field")
        
        log_success(f"Query expanded: '{question}' → '{expanded[:100]}...'")
        return expanded
    
    @staticmethod
    def enhanced_search(
        question: str,
        k: int = 10,
        config: Optional[AgentConfig] = None,
        use_multi_expansion: bool = False,
        num_expansions: int = 3
    ) -> str:
        """
        Perform query expansion enhanced search
        """
        if not question or not question.strip():
            log_warning("Empty query provided to enhanced_search")
            return "No query provided."
        
        log_info(f"Enhanced search initiated: query='{question}', k={k}")
        
        try:
            if use_multi_expansion:
                # Multi-expansion: Generate multiple query variants
                all_queries = set()
                all_queries.add(question)  # Include original
                
                for i in range(num_expansions):
                    log_info(f"Generating expansion {i+1}/{num_expansions}")
                    expanded = QueryExpansionTool.expand_query(question, config)
                    all_queries.add(expanded)
                
                # Search with combined queries
                combined_query = " ".join(all_queries)
                log_info(f"Combined query: '{combined_query[:150]}...'")
                results = vector_db_tool.search_documents(combined_query, k=k)
                
                log_success(f"Multi-expansion search completed with {len(all_queries)} variants")
                return results
                
            else:
                # Single expansion: Expand once and search
                expanded_query = QueryExpansionTool.expand_query(question, config)
                
                # Use the expanded query with standard hybrid search
                results = vector_db_tool.search_documents(expanded_query, k=k)
                
                log_success("Enhanced search completed")
                return results
                
        except Exception as e:
            error_msg = f"Enhanced search failed: {e}"
            log_error(error_msg)
            # Fallback to regular search with original query
            log_warning("Falling back to standard search")
            return vector_db_tool.search_documents(question, k=k)


# Create singleton instances
hyde_tool = HyDETool()
query_expansion_tool = QueryExpansionTool()