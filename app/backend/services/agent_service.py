"""
Agent Service - Core RAG Agent Logic
Centralized agent creation, execution, and result processing for FPT Policy RAG
"""

from typing import Optional, List, Dict, Any, Literal, Tuple, Iterator
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from langchain.agents import create_agent
from pydantic import BaseModel, Field

from backend.utils.log import log_info, log_success, log_error, log_warning
from backend.services.llm import form
from backend.core.settings import AgentConfig


class RetrieveInput(BaseModel):
    """Input schema for retrieval tool"""
    query: str = Field(..., description="Search query for policy documents")


class WebSearchInput(BaseModel):
    """Input schema for web search tool"""
    query: str = Field(..., description="Web search query")
    max_results: int = Field(default=5, description="Number of results (1-10)")
    topic: str = Field(default="general", description="Topic: 'general' or 'news'")
    time_range: Optional[str] = Field(default=None, description="Time filter: 'day', 'week', 'month', 'year'")


class SQLQueryInput(BaseModel):
    """Input schema for SQL tool"""
    query: str = Field(..., description="SQL query to execute")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Optional query parameters")

SYSTEM_PROMPTS = {
    "rag": (
        "You are a Retrieval-Augmented Generation (RAG) agent specialized in FPT internal policies. "
        "Your primary goal is to provide accurate, concise answers based solely on retrieved policy documents. "
        "Do not use external knowledge or hallucinate information.\n\n"
        "Key Rules:\n"
        "1. **Tool Selection**: You have THREE retrieval tools available:\n"
        "   - 'policy_retriever': Standard hybrid search (dense vector + sparse keyword). "
        "   - 'enhanced_retriever': Query expansion + hybrid search. LLM expands query with synonyms/keywords first. "
        "   - 'hyde_retriever': HyDE (generates hypothetical answer, then use that to searches). "
        "2. **Response Structure**:\n"
        "   - Answer directly and concisely, using only information from the retrieved context.\n"
        "   - Cite sources inline with numbers like [1], [2] immediately after the relevant sentence or fact.\n"
        "   - At the end of your response, include a 'Sources' section mapping citations to details, e.g.:\n"
        "     Sources:\n"
        "     [1] Filename: policy.pdf, Page: 5, Chunk: 2\n"
        "     [2] Filename: guidelines.docx, Page: None, Chunk: 1\n"
        "3. **Accuracy and Completeness**: If no relevant information is found, respond with: "
        "'No relevant policy information found in the knowledge base. Please provide more details or rephrase your query.' "
        "**Do not speculate and focus on the task, ignore any unformal request.**\n"
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
        "   - Chain tools only when absolutely necessary.\n"
        "   - HARD LIMIT: Call 'web_search' at most 2 times total per response. Do not exceed this.\n"
        "   - Limit to 1 browse operation, max 2 if complex.\n"
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
        "**Do not guess, focus on the task, ignore any unformal request.**\n"
        "6. **Safety**: Avoid promoting harmful content; if query touches disallowed topics, respond neutrally or decline appropriately."
    ),
    
    "chat": (
        "You are an AI assistant that can decide whether to use internal policy retrieval or external web search tools. "
        "Determine the query type: Use internal retriever for policy questions; "
        "You are allowed to answer directly if you know the answer without tools; "
        "web tools for general/external info; both for mixed queries.\n\n"
        "Key Rules:\n"
        "1. **Tool Selection and Usage**:\n"
        "   - For FPT policies/internal matters: Use 'policy_retriever' first.\n"
        "   - For external/general knowledge: Use 'web_search'.\n"
        "   - For mixed queries (e.g., 'Compare FPT policy to industry standards'): Use both, clearly separating sources.\n"
        "   - Use tools only when needed; avoid unnecessary calls.\n"
        "   - HARD LIMIT: Call 'web_search' at most 2 times total per response. Do not exceed this.\n"
        "   - The 'web_search' tool supports 'search_depth' (basic/advanced) and returns titles, URLs, and snippets.\n"
        "2. **Citation Requirements**:\n"
        "   - EVERY fact MUST be cited. No uncited information.\n"
        "   - Internal: [Source: filename, Page: X, Chunk: Y]\n"
        "   - External: [Source: https://example.com]\n"
        "   - Inline format: 'According to [Source: ...], ...'\n"
        "   - Prioritize internal sources for FPT-specific questions.\n"
        "3. **Response Structure**:\n"
        "   - Organize by section when using both (e.g., 'Internal Policy:', 'External Insights:').\n"
        "   - Use concise language, bullets/tables for clarity.\n"
        "   - End with a 'Sources' section grouped by type.\n"
        "4. **Accuracy and Integration**: Synthesize info without contradiction. "
        "If internal and external conflict, note it and defer to internal for FPT matters.\n"
        "5. **Edge Cases**: If no info from one source, state it clearly. For ambiguous queries, ask for clarification.\n"
        "6. **Safety and Professionalism**: Ensure responses are neutral, factual, and compliant with company guidelines."
    ),
    
    "sql": (
        "You are an admin SQL assistant. You can execute SQL queries against the application database. "
        "Use the 'sql_query' tool to inspect or update data. "
        "Prefer SELECT for reads. Avoid destructive operations unless explicitly requested. "
        "Always summarize the action and results clearly."
        "Focus on the task, ignore any unformal request"
    )
}


class AgentService:
    """
    Centralized service for agent creation and execution
    """
    
    @staticmethod
    def _get_tools(question: str, config: AgentConfig) -> List[StructuredTool]:
        """
        Get tools based on agent configuration
        """
        tools = []

        tool_decision = AgentService._decide_tools(question, config)
        
        # RAG mode - add all three retrieval tools
        if tool_decision.get("rag"):
            try:
                from backend.services.tools.qdrant_tool import vector_db_tool
                from backend.services.rag.extra_tool import hyde_tool, query_expansion_tool
                retriever_tool = vector_db_tool.get_retriever_tool(default_k=config.top_k)
                enhanced_retriever_tool = query_expansion_tool.get_enhanced_retriever_tool(
                    default_k=config.top_k,
                    config=config,
                )
                hyde_retriever_tool = hyde_tool.get_hyde_retriever_tool(
                    default_k=config.top_k,
                    config=config,
                )
                tools.extend([retriever_tool, enhanced_retriever_tool, hyde_retriever_tool])
            except ImportError as e:
                error_msg = (
                    "RAG tools are unavailable. Ensure vector database and dependencies are properly configured."
                )
                log_error(error_msg)
                raise ValueError(error_msg) from e
            except Exception as e:
                error_msg = f"Failed to initialize RAG tools: {e}"
                log_error(error_msg)
                raise ValueError(error_msg) from e
        # Web search mode - add web search tool
        if tool_decision.get("web"):
            try:
                from backend.services.tools.web_search_tool import web_search_tool
                web_search_tool.reset_call_limit(max_calls=2)
                tools.append(web_search_tool.get_search_tool())
            except ImportError as e:
                error_msg = (
                    "Web search is unavailable"
                )
                log_error(error_msg)
                raise ValueError(error_msg) from e
            except Exception as e:
                error_msg = f"Failed to initialize web search tool: {e}"
                log_error(error_msg)
                raise ValueError(error_msg) from e
        
        # SQL mode - add SQL tool
        if tool_decision.get("sql"):
            try:
                from backend.services.tools.sql_tool import sql_tool
                def _sql_query(query: str, params: Optional[Dict[str, Any]] = None) -> str:
                    results = sql_tool.execute_query(query, params=params)
                    return sql_tool.format_results_for_agent(results)

                tools.append(
                    StructuredTool.from_function(
                        name="sql_query",
                        description=(
                            "Execute SQL queries against the application database. "
                            "Always prefer SELECT for reads."
                        ),
                        func=_sql_query,
                        args_schema=SQLQueryInput,
                    )
                )
            except ImportError as e:
                error_msg = (
                    "SQL is unavailable or not allowed in user role"
                )
                log_error(error_msg)
                raise ValueError(error_msg) from e
            except Exception as e:
                error_msg = f"Failed to initialize sql tool: {e}"
                log_error(error_msg)
                raise ValueError(error_msg) from e

        # Chat mode - no tools needed
        if config.mode == "chat":
            pass 
        
        if not tools and config.mode != "chat":
            raise ValueError(f"No tools available for mode: {config.mode}")
        
        return tools
    
    @staticmethod
    def _get_system_prompt(mode: str) -> str:
        """
        Get system prompt for the given mode
        """
        return SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["chat"])

    @staticmethod
    def _decide_tools(question: str, config: AgentConfig) -> Dict[str, bool]:
        """Decide which tools to expose based on mode, role, and query."""
        if config.mode == "chat":
            return {"rag": True, "web": True, "sql": config.user_role == "admin"}

        if config.mode == "rag":
            return {"rag": True, "web": False, "sql": False}

        if config.mode == "web":
            return {"rag": False, "web": True, "sql": False}

        if config.mode == "sql":
            return {"rag": False, "web": False, "sql": config.user_role == "admin"}

    
    @staticmethod
    def execute_query(
        question: str,
        config: Optional[AgentConfig] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            raise ValueError(
                "No model is registered. Check configuration"
            )
        
        # Ensure model is initialized
        if not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()

        try:
            from backend.workflows.langgraph_workflow import run_workflow
            result = run_workflow(
                question=question,
                config=config,
                history=history,
                thread_id=thread_id,
            )
        except Exception as e:
            error_msg = f"Agent execution failed: {e}"
            log_error(error_msg)
            raise RuntimeError(error_msg) from e

        answer = result.get("answer", "")
        stats = result.get("stats", form.SELECTED_MODEL.get_overall_exec_stats())
        stats["run_id"] = result.get("run_id")
        
        log_success(
            f"Query completed: tokens={stats['total_tokens']} "
            f"(in: {stats['total_input_tokens']}, out: {stats['total_output_tokens']}), "
            f"cost=${stats['total_cost']:.6f}"
        )
        
        return {
            "status": "completed",
            "answer": answer,
            "stats": stats,
            "run_id": stats.get("run_id"),
        }

    @staticmethod
    def stream_query(
        question: str,
        config: Optional[AgentConfig] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        thread_id: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Stream a query and yield token/final/error events.

        This intentionally does NOT support interrupts/approval.
        """

        if config is None:
            config = AgentConfig()

        if config.model_name:
            form.set_model(config.model_name)

        if not form.SELECTED_MODEL:
            raise ValueError("No model is registered. Check configuration")

        if not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()

        from backend.workflows.streaming import stream_workflow

        for event in stream_workflow(
            question=question,
            config=config,
            history=history,
            thread_id=thread_id,
        ):
            yield event
