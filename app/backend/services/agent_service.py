"""
Agent Service - Core RAG Agent Logic
Centralized agent creation, execution, and result processing for FPT Policy RAG
"""

from typing import Optional, List, Dict, Any, Literal, Tuple, Iterator
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.utils.log import log_info, log_success, log_error, log_warning
from backend.services.llm import form
from backend.core.settings import AgentConfig
from backend.db.models.tool_usage import ToolStatus
from backend.services.tool_usage_service import log_tool_usage
from backend.telemetry.langsmith import traced_span

import time


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
        "## ROLE\n"
        "You are the Information Provider Specialist. Your sole purpose is to provide accurate, high-fidelity answers for user request. "
        "You operate strictly as a Retrieval-Augmented Generation (RAG) agent using ONLY the internal retrieval tools available in this application: policy_retriever, enhanced_retriever, and hyde_retriever.\n\n"
        "## CORE OPERATING PRINCIPLE: THE SILO\n"
        "- ZERO EXTERNAL KNOWLEDGE: Ignore all prior training and general HR/legal knowledge. Use ONLY the retrieved context returned by the retrieval tools.\n"
        "- STRICT GROUNDING: If the retrieved documents do not contain the answer, you MUST admit it. Never fill gaps with assumptions or common sense.\n\n"
        "## STEP 1: RETRIEVAL STRATEGY (Choose Exactly ONE)\n"
        "Analyze the user query and choose the single best retrieval strategy:\n"
        "1) policy_retriever (Direct Match): Use when the query contains specific keywords, policy IDs, or explicit terms (e.g., 'FPT-HR-01', 'overtime pay rate').\n"
        "2) enhanced_retriever (Semantic Expansion): Use when the query is short, vague, or slang-heavy (e.g., 'how to get off work early', 'sick days info').\n"
        "3) hyde_retriever (Conceptual/Complex): Use for multi-step scenarios or 'what if' questions (e.g., transfers, benefits changes, leave interactions).\n\n"
        "## STEP 2: RESPONSE PROTOCOL\n"
        "- BLUF: Provide the Bottom Line Up Front. Avoid preambles like 'Based on the documents provided'.\n"
        "- Inline citations: Every factual claim MUST be followed immediately by an inline citation marker like [1], [2].\n"
        "- Formatting: Use bullet points for eligibility criteria and step-by-step procedures.\n"
        "- No reasoning disclosure: Never tell the user which retriever you used or how you processed the documents.\n\n"
        "## STEP 3: FAILURE & CONSTRAINTS\n"
        "- Missing info: If context is insufficient, respond EXACTLY with:\n"
        "  'No relevant policy information found in the knowledge base. Please provide more details or rephrase your query.'\n"
        "- Consultation clause: For high-stakes HR or Legal topics (termination, disputes, compliance, contracts, disciplinary actions), include:\n"
        "  'Please consult with your HR Business Partner for official confirmation.'\n\n"
        "## SOURCE CITATION FORMAT\n"
        "End with a Sources section mapping citation numbers to document metadata. Use this format:\n"
        "Sources:\n"
        "[1] Filename: <name>, Page: <page or None>, Chunk: <chunk id>\n"
        "[2] Filename: <name>, Page: <page or None>, Chunk: <chunk id>\n\n"
        "## STYLE & LANGUAGE\n"
        "- Match the user's language (e.g., Vietnamese queries -> Vietnamese answers).\n"
        "- Tone: Professional, neutral, and authoritative."
    ),
    
    "web": (
        "## ROLE\n"
        "You are a high-precision Information Assistant. Your mission is to provide synthesized, verified, and timely answers. "
        "You balance general knowledge with live web data via the available tools in this application.\n\n"
        "Important: In THIS app, you have access to the 'web_search' tool (returns titles, URLs, and snippets). "
        "Do NOT claim you opened pages or read full articles unless that content is present in tool results.\n\n"
        "## 1. THE REASONING LOOP (Pre-Action)\n"
        "Before responding or triggering a tool, do a silent mental check:\n"
        "- Knowledge Gap: Do I already have enough reliable information to answer?\n"
        "- Volatility: Is this a living topic (news, earnings, prices, versions) that needs freshness?\n"
        "- Verification: Does the user need citations or high-stakes accuracy?\n\n"
        "## 2. SEARCH TRIGGERING LOGIC\n"
        "Trigger web_search ONLY when one of these is true:\n"
        "- Temporal cues: now/today/current/latest/recent/this week/this month\n"
        "- Volatile data: prices, breaking news, rankings, product availability, software versions\n"
        "- Specific entity lookups: a company update, filing, press release, policy/regulatory change\n"
        "- Low confidence: you are not confident in core facts (confidence < 0.80)\n"
        "- Explicit request: the user asks you to search/look up/find sources\n\n"
        "## 3. SEARCH & EVIDENCE STRATEGY\n"
        "- Multi-perspective fan-out: use 2–4 distinct queries maximum (official source + reputable news + reference docs as needed).\n"
        "- Depth over breadth: prefer refining queries (site:, date terms, exact names) over running many similar searches.\n"
        "- Source hierarchy: prioritize primary/official sources first (company IR/newsroom, regulators, standards bodies), then major reputable outlets.\n"
        "- Efficiency: stop searching once you can answer; do not 'keep searching just in case'.\n"
        "- Tool limits: respect the run budget; keep web_search calls minimal. (2 to 5)\n\n"
        "## 4. SYNTHESIS & CITATIONS (RAG-STYLE)\n"
        "- Use inline numbered citations like [1], [2] immediately after factual claims.\n"
        "- Reuse the same number for the same URL throughout the answer.\n"
        "- Synthesize and paraphrase; do not copy large blocks of text.\n"
        "- If sources disagree, present the discrepancy and cite both; include dates when available.\n"
        "- If you cannot cite a claim from the tool results, omit it.\n\n"
        "## 5. OUTPUT ARCHITECTURE\n"
        "- BLUF: Start with a short, direct answer in a natural conversational tone.\n"
        "- Evidence: Follow with concise bullets/short paragraphs driven strictly by what the sources say (no filler background).\n"
        "- Sources: End with a clean list mapping citations to Source metadata:\n"
        "  Sources:\n"
        "  [1] Title — Publisher (if known), Date (if known) — URL\n"
        "  [2] ...\n"
        "- Unverified flag: If web_search returns no reliable results, say: 'I am relying on general knowledge; live verification was unavailable.'\n\n"
        "## 6. CONSTRAINTS & SAFETY\n"
        "- Privacy: never include secrets/credentials/PII in queries.\n"
        "- Copyright: respect paywalls; do not claim access to restricted content.\n"
        "- Safety: follow policy; refuse disallowed requests.\n\n"
    ),
    
    "chat": (
        "## ROLE\n"
        "You are a high-precision assistant that can answer using either (a) FPT internal policy retrieval (RAG) or (b) live web search. "
        "In this application, chat mode includes ONLY these tools: policy_retriever, enhanced_retriever, hyde_retriever, and web_search.\n\n"
        "## CORE PRINCIPLE\n"
        "- For FPT internal policy questions: operate in 'THE SILO' (use ONLY retrieved internal context; no outside knowledge).\n"
        "- For external/current questions: use web_search and cite URLs.\n"
        "- Never mix internal and external claims without clearly separating and citing them.\n\n"
        "## 1. THE REASONING LOOP (Pre-Action)\n"
        "Before responding or triggering a tool, do a silent mental check:\n"
        "- Is this an FPT internal policy question? (HR policy, benefits, procedures, internal rules)\n"
        "- Is it time-sensitive/external? (latest/current/news/versions/prices)\n"
        "- Do I need verification via citations?\n\n"
        "## 2. TOOL SELECTION\n"
        "Choose the minimum tools needed:\n"
        "- Internal policy queries: use EXACTLY ONE retrieval strategy (policy_retriever OR enhanced_retriever OR hyde_retriever).\n"
        "- External queries: use web_search (2–4 calls max; avoid near-duplicates).\n"
        "- Mixed queries: do internal retrieval for the FPT part AND web_search for the external part, and keep the outputs separated.\n\n"
        "## 3. CITATIONS (Numbered, RAG-style)\n"
        "- Every factual claim must have an inline citation marker like [1], [2] immediately after the sentence.\n"
        "- Sources can be internal docs (Filename/Page/Chunk) or external URLs, but all are listed in ONE numbered Sources section.\n"
        "- If you cannot cite a claim from tool results, omit it.\n\n"
        "## 4. OUTPUT ARCHITECTURE\n"
        "- BLUF: Start with a short, direct answer in a natural conversational tone.\n"
        "- If mixed: split into sections 'Internal Policy' and 'External Information'.\n"
        "- Use bullets for steps/eligibility.\n"
        "- End with:\n"
        "  Sources:\n"
        "  [1] Filename: <name>, Page: <page or None>, Chunk: <chunk id>\n"
        "  [2] Title — Publisher (if known), Date (if known) — URL\n\n"
        "## 5. EDGE CASES\n"
        "- If internal policy context is insufficient, respond EXACTLY:\n"
        "  'No relevant policy information found in the knowledge base. Please provide more details or rephrase your query.'\n"
        "- If web_search returns no reliable results, say:\n"
        "  'I am relying on general knowledge; live verification was unavailable.'\n\n"
        "## 6. STYLE & SAFETY\n"
        "- Match the user's language.\n"
        "- Tone: professional, neutral, and helpful.\n"
        "- Follow safety policy; refuse disallowed requests."
    ),
    
    "sql": (
        "# SYSTEM PROMPT: Database SQL Assistant\n\n"
        "## ROLE\n"
        "You are a careful SQL assistant for the application database. Your job is to run SQL safely and summarize results clearly.\n\n"
        "## SAFETY & CONSTRAINTS\n"
        "- Prefer SELECT queries.\n"
        "- Never run INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE unless the user explicitly requests the change.\n"
        "- If the user asks for a destructive change, ask a clarification confirming scope (tables/rows/filters) before executing.\n"
        "- Avoid returning sensitive data unless explicitly needed; prefer aggregated results.\n"
        "- Use parameters when appropriate (avoid string interpolation).\n\n"
        "## EXECUTION PROTOCOL\n"
        "- If the request is ambiguous, ask 1–2 clarifying questions before querying.\n"
        "- For reads, keep results small (use LIMIT) unless the user requests full export.\n"
        "- If an error occurs, explain it briefly and propose a corrected query.\n\n"
        "## OUTPUT FORMAT\n"
        "- Start with a one-line summary of what you did.\n"
        "- Show the SQL you executed (or a concise description if long).\n"
        "- Provide the key results and any caveats.\n"
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
        tools: List[StructuredTool] = []

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

        # Chat mode - all tool
        if config.mode == "chat":
            # Implement all tool in this mode
            pass
            
        
        if not tools and config.mode != "chat":
            raise ValueError(f"No tools available for mode: {config.mode}")
        
        return AgentService._instrument_tools(tools, config=config)

    @staticmethod
    def _instrument_tools(tools: List[StructuredTool], *, config: AgentConfig) -> List[StructuredTool]:
        """Wrap tool execution with tracing + logging.

        This is intentionally best-effort: if tracing/logging fails, tools still run.
        """
        instrumented: List[StructuredTool] = []
        for tool in tools or []:
            try:
                instrumented.append(AgentService._instrument_tool(tool, config=config))
            except Exception as e:
                log_warning(f"Tool instrumentation skipped for {getattr(tool, 'name', '?')}: {e}")
                instrumented.append(tool)
        return instrumented

    @staticmethod
    def _instrument_tool(tool: StructuredTool, *, config: AgentConfig) -> StructuredTool:
        name = getattr(tool, "name", "tool")
        original_func = getattr(tool, "func", None)
        original_coroutine = getattr(tool, "coroutine", None)

        def _log_and_trace_success(*, duration_ms: int, input_data: Dict[str, Any], output_text: str) -> None:
            try:
                log_tool_usage(
                    tool_name=name,
                    status=ToolStatus.SUCCESS,
                    input_data=input_data,
                    output_preview=(output_text or "")[:2000],
                )
            except Exception:
                # Tool usage logging must never break execution.
                return

        def _log_and_trace_error(*, duration_ms: int, input_data: Dict[str, Any], err: Exception) -> None:
            try:
                log_tool_usage(
                    tool_name=name,
                    status=ToolStatus.FAILED,
                    input_data=input_data,
                    output_preview="",
                    error_message=str(err),
                )
            except Exception:
                return

        def wrapped_func(*args, **kwargs):
            # Most StructuredTool calls will pass only kwargs matching args_schema.
            input_data: Dict[str, Any] = {}
            try:
                input_data = dict(kwargs) if kwargs else {"args": list(args)}
            except Exception:
                input_data = {"args": "<unserializable>", "kwargs": "<unserializable>"}

            log_info(f"Tool start: {name}")
            start = time.perf_counter()
            with traced_span(
                name=f"tool.{name}",
                run_type="tool",
                inputs={
                    "tool": name,
                    "mode": getattr(config, "mode", None),
                    "input": input_data,
                },
            ) as span:
                try:
                    if original_func is None:
                        raise RuntimeError("Tool has no callable func")
                    result = original_func(*args, **kwargs)
                    # Tool outputs can be large; keep trace payload compact.
                    output_text = result if isinstance(result, str) else str(result)
                    duration_ms = int((time.perf_counter() - start) * 1000)
                    span.set_outputs(
                        {
                            "output_preview": (output_text or "")[:2000],
                            "duration_ms": duration_ms,
                        }
                    )
                    _log_and_trace_success(duration_ms=duration_ms, input_data=input_data, output_text=output_text)
                    log_success(f"Tool success: {name} ({duration_ms} ms)")
                    return result
                except Exception as e:
                    duration_ms = int((time.perf_counter() - start) * 1000)
                    span.add_metadata(duration_ms=duration_ms)
                    _log_and_trace_error(duration_ms=duration_ms, input_data=input_data, err=e)
                    log_error(f"Tool failed: {name} ({duration_ms} ms): {e}")
                    raise

        # Async tools: best-effort wrap if present.
        async def wrapped_coroutine(*args, **kwargs):  # type: ignore[no-redef]
            input_data: Dict[str, Any] = {}
            try:
                input_data = dict(kwargs) if kwargs else {"args": list(args)}
            except Exception:
                input_data = {"args": "<unserializable>", "kwargs": "<unserializable>"}

            log_info(f"Tool start: {name}")
            start = time.perf_counter()
            with traced_span(
                name=f"tool.{name}",
                run_type="tool",
                inputs={
                    "tool": name,
                    "mode": getattr(config, "mode", None),
                    "input": input_data,
                },
            ) as span:
                try:
                    if original_coroutine is None:
                        raise RuntimeError("Tool has no coroutine")
                    result = await original_coroutine(*args, **kwargs)
                    output_text = result if isinstance(result, str) else str(result)
                    duration_ms = int((time.perf_counter() - start) * 1000)
                    span.set_outputs({"output_preview": (output_text or "")[:2000], "duration_ms": duration_ms})
                    _log_and_trace_success(duration_ms=duration_ms, input_data=input_data, output_text=output_text)
                    log_success(f"Tool success: {name} ({duration_ms} ms)")
                    return result
                except Exception as e:
                    duration_ms = int((time.perf_counter() - start) * 1000)
                    span.add_metadata(duration_ms=duration_ms)
                    _log_and_trace_error(duration_ms=duration_ms, input_data=input_data, err=e)
                    log_error(f"Tool failed: {name} ({duration_ms} ms): {e}")
                    raise

        # Mutate tool to preserve all metadata/args_schema.
        if original_func is not None:
            tool.func = wrapped_func  # type: ignore[assignment]
        if original_coroutine is not None:
            tool.coroutine = wrapped_coroutine  # type: ignore[assignment]
        return tool
    
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
            # Chat mode intentionally supports ONLY RAG + web search tools.
            return {"rag": True, "web": True, "sql": False}

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
        checkpoint_id: Optional[str] = None,
        checkpoint_ns: Optional[str] = None,
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

        # Initialize per-run tool budgets (enforced in tool implementation)
        try:
            tool_decision = AgentService._decide_tools(question, config)
            if tool_decision.get("web"):
                from backend.services.tools.web_search_tool import web_search_tool
                max_calls = int(getattr(config, "web_search_max_calls", 6) or 6)
                max_results = int(getattr(config, "web_search_max_results", 5) or 5)
                dedupe = bool(getattr(config, "web_search_dedupe", True))
                web_search_tool.configure_run(max_calls=max_calls, max_results=max_results, dedupe=dedupe)
        except Exception as e:
            log_warning(f"Failed to configure web search run budget: {e}")

        try:
            tools = AgentService._get_tools(question, config)
            system_prompt = AgentService._get_system_prompt(config.mode)
            from backend.workflows.langgraph_workflow import run_workflow
            result = run_workflow(
                question=question,
                config=config,
                history=history,
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                checkpoint_ns=checkpoint_ns,
                tools=tools,
                system_prompt=system_prompt,
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
        checkpoint_id: Optional[str] = None,
        checkpoint_ns: Optional[str] = None,
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

        # Initialize per-run tool budgets (enforced in tool implementation)
        try:
            tool_decision = AgentService._decide_tools(question, config)
            if tool_decision.get("web"):
                from backend.services.tools.web_search_tool import web_search_tool
                max_calls = int(getattr(config, "web_search_max_calls", 6) or 6)
                max_results = int(getattr(config, "web_search_max_results", 5) or 5)
                dedupe = bool(getattr(config, "web_search_dedupe", True))
                web_search_tool.configure_run(max_calls=max_calls, max_results=max_results, dedupe=dedupe)
        except Exception as e:
            log_warning(f"Failed to configure web search run budget: {e}")

        tools = AgentService._get_tools(question, config)
        system_prompt = AgentService._get_system_prompt(config.mode)
        from backend.workflows.streaming import stream_workflow

        for event in stream_workflow(
            question=question,
            config=config,
            history=history,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=checkpoint_ns,
            tools=tools,
            system_prompt=system_prompt,
        ):
            yield event
