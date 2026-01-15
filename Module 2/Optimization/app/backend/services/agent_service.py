"""
Agent Service - Core RAG Agent Logic
Centralized agent creation, execution, and result processing for FPT Policy RAG
"""

from typing import Optional, List, Dict, Any, Literal, Tuple
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from langchain.agents import create_agent
from pydantic import BaseModel, Field

from app.backend.services.qdrant import vector_db_tool
from app.backend.services.extra_tool import hyde_tool, query_expansion_tool
from app.backend.utils.log import log_info, log_success, log_error, log_warning
from app.backend.api import form
from app.backend.config import AgentConfig


class RetrieveInput(BaseModel):
    """Input schema for retrieval tool"""
    query: str = Field(..., description="Search query for policy documents")


class WebSearchInput(BaseModel):
    """Input schema for web search tool"""
    query: str = Field(..., description="Web search query")
    max_results: int = Field(default=5, description="Number of results (1-20)")
    topic: str = Field(default="general", description="Topic: 'general' or 'news'")
    time_range: Optional[str] = Field(default=None, description="Time filter: 'day', 'week', 'month', 'year'")


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

SYSTEM_PROMPTS = {
    "rag": (
        "You are a Retrieval-Augmented Generation (RAG) agent specialized in FPT internal policies. "
        "Your primary goal is to provide accurate, concise answers based solely on retrieved policy documents. "
        "Do not use external knowledge or hallucinate information.\n\n"
        "Key Rules:\n"
        "1. **Tool Selection**: You have THREE retrieval tools available:\n"
        "   - 'policy_retriever': Standard hybrid search (dense vector + sparse keyword). "
        "Use for simple queries with clear keywords.\n"
        "   - 'enhanced_retriever': Query expansion + hybrid search. LLM expands query with synonyms/keywords first. "
        "**RECOMMENDED for most queries**, especially complex or abstract ones.\n"
        "   - 'hyde_retriever': HyDE (generates hypothetical document, then searches). "
        "Most powerful but expensive. Use only for highly semantic/conceptual queries.\n\n"
        "   **Strategy**: Start with 'enhanced_retriever' for most questions. "
        "Use 'policy_retriever' for simple keywords. "
        "Use 'hyde_retriever' only if other methods fail or query is extremely abstract.\n\n"
        "2. **Response Structure**:\n"
        "   - Answer directly and concisely, using only information from the retrieved context.\n"
        "   - Cite sources inline with numbers like [1], [2] immediately after the relevant sentence or fact.\n"
        "   - At the end of your response, include a 'Sources' section mapping citations to details, e.g.:\n"
        "     Sources:\n"
        "     [1] Filename: policy.pdf, Page: 5, Chunk: 2\n"
        "     [2] Filename: guidelines.docx, Page: None, Chunk: 1\n"
        "3. **Accuracy and Completeness**: If no relevant information is found, respond with: "
        "'No relevant policy information found in the knowledge base. Please provide more details or rephrase your query.' "
        "Do not speculate.\n"
        "4. **Conciseness**: Keep responses brief and to the point. Use bullet points or numbered lists for clarity when appropriate.\n"
        "5. **Language**: Respond in the user's language if specified; otherwise, use professional English.\n"
        "6. **Edge Cases**: For sensitive topics (e.g., HR, legal), emphasize consulting official channels if the retrieved info is advisory."
    ),
    
    "web": (
        "You are a web research assistant powered by real-time web search tools. "
        "Your role is to gather and synthesize accurate information from the internet, "
        "always backing every claim with verifiable sources. Never provide unsubstantiated facts or opinions.\n\n"
        "Key Rules:\n"
        "1. **Tool Usage**:\n"
        "   - Use the 'web_search' tool for general queries. Include site: operators for targeted searches (e.g., site:gov for official info).\n"
        "   - If a source URL needs deeper analysis, use 'browse_page' with specific instructions.\n"
        "   - Chain tools if needed: Search first, then browse top results for details.\n"
        "   - Limit to 1-2 tool calls per response unless complex.\n"
        "2. **Citation Requirements**:\n"
        "   - EVERY fact, statistic, or non-obvious statement MUST have a citation.\n"
        "   - Format inline: 'According to [Source: https://example.com], ...'\n"
        "   - Use short, relevant URLs; avoid tracking params.\n"
        "   - If multiple sources support a point, cite the most authoritative first.\n"
        "3. **Response Structure**:\n"
        "   - Start with a brief summary if the query is broad.\n"
        "   - Use headings, bullets, or tables for organized output.\n"
        "   - End with a 'Sources' section listing all unique URLs with brief descriptions.\n"
        "4. **Accuracy and Bias Handling**: Cross-reference multiple sources for controversial topics. "
        "Note any discrepancies. Prefer recent, reputable sites.\n"
        "5. **Edge Cases**: If no reliable info found, say: 'Insufficient reliable information available from web search.' "
        "Do not guess.\n"
        "6. **Safety**: Avoid promoting harmful content; if query touches disallowed topics, respond neutrally or decline appropriately."
    ),
    
    "hybrid": (
        "You are a hybrid research assistant combining FPT internal policies with external web information. "
        "Determine the query type to choose tools: Use internal retriever for policy questions; "
        "web tools for general/external info; both for mixed queries.\n\n"
        "Key Rules:\n"
        "1. **Tool Selection and Usage**:\n"
        "   - For FPT policies/internal matters: Use 'policy_retriever' first.\n"
        "   - For external/general knowledge: Use 'web_search' and/or 'browse_page'.\n"
        "   - For hybrid queries (e.g., 'Compare FPT policy to industry standards'): Use both, clearly separating sources.\n"
        "   - Always retrieve before answering. Chain tools logically.\n"
        "2. **Citation Requirements**:\n"
        "   - EVERY fact MUST be cited. No uncited information.\n"
        "   - Internal: [Source: filename, Page: X, Chunk: Y]\n"
        "   - External: [Source: https://example.com]\n"
        "   - Inline format: 'According to [Source: ...], ...'\n"
        "   - Prioritize internal sources for FPT-specific questions.\n"
        "3. **Response Structure**:\n"
        "   - Organize by section if hybrid (e.g., 'Internal Policy:', 'External Insights:').\n"
        "   - Use concise language, bullets/tables for clarity.\n"
        "   - End with a 'Sources' section grouped by type.\n"
        "4. **Accuracy and Integration**: Synthesize info without contradiction. "
        "If internal and external conflict, note it and defer to internal for FPT matters.\n"
        "5. **Edge Cases**: If no info from one source, state it clearly. For ambiguous queries, ask for clarification.\n"
        "6. **Safety and Professionalism**: Ensure responses are neutral, factual, and compliant with company guidelines."
    ),
    
    "chat": (
        "You are a helpful AI assistant. Provide clear, accurate, and concise answers. "
        "Be professional and friendly. If you don't know something, say so."
    )
}


class AgentService:
    """
    Centralized service for agent creation and execution
    """
    
    @staticmethod
    def _get_tools(config: AgentConfig) -> List[StructuredTool]:
        """
        Get tools based on agent configuration
        """
        tools = []
        
        # RAG mode - add all three retrieval tools
        if config.mode in {"rag", "hybrid"}:
            # Tool 1: Standard retrieval (hybrid: dense + sparse)
            retriever_tool = StructuredTool.from_function(
                name="policy_retriever",
                description=(
                    "Standard hybrid search (dense vector + sparse keyword) in FPT policy knowledge base. "
                    "Use for straightforward queries with clear keywords. "
                    "Fast and reliable for direct matches."
                    "RECOMMENDED for simple, specific queries."
                ),
                func=lambda query: vector_db_tool.search_documents(query, k=config.top_k),
                args_schema=RetrieveInput,
            )
            
            # Tool 2: Query Expansion
            enhanced_retriever_tool = StructuredTool.from_function(
                name="enhanced_retriever",
                description=(
                    "Query expansion retrieval tool."
                    "First uses LLM to reformulate/expand query with better keywords and synonyms, "
                    "then performs hybrid search (dense + sparse). "
                    "RECOMMENDED for complex or too short queries where keywords may be insufficient."
                ),
                func=lambda query: query_expansion_tool.enhanced_search(query, k=config.top_k, config=config),
                args_schema=RetrieveInput,
            )
            
            # Tool 3: HyDE (Hypothetical Document Embeddings)
            hyde_retriever_tool = StructuredTool.from_function(
                name="hyde_retriever",
                description=(
                    "HyDE (Hypothetical Document Embeddings) search. "
                    "Generates a complete hypothetical answer first, then searches for similar documents. "
                    "Use for highly conceptual/semantic queries where keyword matching completely fails. "
                    "More expensive than enhanced_retriever - use only when needed."
                    "RECOMMENDED for abstract queries lacking clear keywords."
                ),
                func=lambda query: hyde_tool.hyde_search(query, k=config.top_k, config=config),
                args_schema=RetrieveInput,
            )
            
            tools.extend([retriever_tool, enhanced_retriever_tool, hyde_retriever_tool])
        
        # Web search mode - add web search tool
        if config.mode in {"web", "hybrid"}:
            try:
                from app.backend.services.web_search import web_search_tool
                tools.append(web_search_tool.get_search_tool())
            except ImportError as e:
                error_msg = (
                    "Web search is unavailable. Install required dependencies: "
                    "pip install langchain-tavily"
                )
                log_error(error_msg)
                raise ValueError(error_msg) from e
            except Exception as e:
                error_msg = f"Failed to initialize web search tool: {e}"
                log_error(error_msg)
                raise ValueError(error_msg) from e
        
        # Chat mode - no tools needed
        if config.mode == "chat":
            pass  # No tools for chat mode
        
        if not tools and config.mode != "chat":
            raise ValueError(f"No tools available for mode: {config.mode}")
        
        return tools
    
    @staticmethod
    def _get_system_prompt(mode: str) -> str:
        """
        Get system prompt for the given mode
        
        Args:
            mode: Agent mode
            
        Returns:
            System prompt string
        """
        return SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["chat"])
    
    @staticmethod
    def execute_query(
        question: str,
        config: Optional[AgentConfig] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Execute a query using the RAG agent
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
        if not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()
        
        # Get tools and system prompt
        try:
            tools = AgentService._get_tools(config)
            system_prompt = AgentService._get_system_prompt(config.mode)
        except ValueError as e:
            raise ValueError(f"Configuration error: {e}") from e
        
        # Log agent creation
        tool_count = len(tools)
        log_info(
            f"Creating agent: mode={config.mode}, tools={tool_count}, "
            f"model={form.SELECTED_MODEL.name}, top_k={config.top_k}"
        )
        
        # Create and execute agent
        try:
            agent = create_agent(
                form.SELECTED_MODEL.llm,
                tools=tools,
                system_prompt=system_prompt
            )
            
            result = agent.invoke({
                "messages": [HumanMessage(content=question)]
            })
        except Exception as e:
            error_msg = f"Agent execution failed: {e}"
            log_error(error_msg)
            raise RuntimeError(error_msg) from e
        
        # Extract answer
        messages = result.get("messages", [])
        answer = getattr(messages[-1], "content", "") if messages else ""
        
        if not answer:
            log_warning("Agent returned empty response")
            answer = "No response generated. Please try rephrasing your question."
        
        # Get execution statistics
        stats = form.SELECTED_MODEL.get_overall_exec_stats()
        
        log_success(
            f"Query completed: tokens={stats['total_tokens']} "
            f"(in: {stats['total_input_tokens']}, out: {stats['total_output_tokens']}), "
            f"cost=${stats['total_cost']:.6f}"
        )
        
        return answer, stats
    
    @staticmethod
    def validate_config(config: AgentConfig) -> Tuple[bool, Optional[str]]:
        """
        Validate agent configuration
        """
        try:
            # Validate mode
            if config.mode not in {"rag", "web", "hybrid", "chat"}:
                return False, f"Invalid mode: {config.mode}"
            
            # Validate top_k
            if config.top_k <= 0:
                return False, "top_k must be greater than 0"
            
            # Check if web search dependencies are available for web/hybrid modes
            if config.mode in {"web", "hybrid"}:
                try:
                    from app.backend.services.web_search import web_search_tool
                except ImportError:
                    return False, "Web search mode requires langchain-tavily. Install: pip install langchain-tavily"
            
            return True, None
            
        except Exception as e:
            return False, str(e)