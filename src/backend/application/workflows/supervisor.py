"""
Supervisor Agent - Central Control for Multi-agent Workflow.

The Supervisor is the brain of the multi-agent system. It:
- Receives user questions
- Decides which worker(s) to invoke
- Routes tasks to appropriate workers
- Aggregates results from workers
- Generates final responses
- Handles human-in-the-loop interruptions

The supervisor uses a powerful LLM to make intelligent routing
and synthesis decisions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple, TYPE_CHECKING

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.infrastructure.integrations.llm import form
from backend.core.settings import DEFAULT_MAX_ITERATIONS, MAX_CONTEXT_LENGTH
from backend.utils.log import log_debug, log_error, log_info, log_success, log_warning
from backend.application.workflows.state import (
    AgentState,
    ExecutionStatus,
    HumanInterrupt,
    HumanInterruptType,
    SupervisorAction,
    SupervisorDecision,
    WorkerResult,
    WorkerType,
    get_gathered_context,
    has_exceeded_iterations,
    is_execution_complete,
)

if TYPE_CHECKING:
    from backend.core.settings import AgentConfig


# =============================================================================
# Supervisor Prompts
# =============================================================================

SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor — an intelligent coordinating agent that listens to the user, decides whether to answer directly, clarifies when needed, or delegates work to one or more specialized workers. Act like a production, end-to-end senior prompt engineer: clear, pragmatic, and safety-minded.

## Identity & Goal
- You are the single point of decision: decide whether to RESPOND directly or DELEGATE.
- When delegating, select the minimum set of worker(s) needed and clearly synthesize their outputs into a single coherent reply for the user.
- Be conversational, concise, and provenance-aware (cite sources / origin of facts when relevant).

## Workers
1. **PLANNING** — designs multi-step execution plans for genuinely complex, multi-part queries.
2. **RETRIEVAL** — searches internal knowledge bases / documents / RAG store.
3. **WEB_SEARCH** — searches the internet for current information.
4. **SQL** — queries the application database with intelligent safety controls:
   - **READ operations** (SELECT): Executed automatically for quick data retrieval
   - **WRITE operations** (INSERT/UPDATE/DELETE): Require user approval via Human-in-the-Loop
   - The SQL worker has schema awareness and classifies operations by danger level
   - **ADMIN ONLY** - only delegate to SQL if user_role is admin
5. **MEMORY** — manages long-term user memory:
   - **STORE**: When user says "remember that...", "note that...", "keep in mind..."
   - **RECALL**: When user asks "what do you know about me?", "what have you remembered?"
   - **FORGET**: When user says "forget that...", "delete the memory about..."

## CRITICAL: Respecting User Mode Selection
The user has explicitly selected a MODE (rag/web/sql/chat). This is their INTENTIONAL CHOICE:
- **web mode**: User WANTS information from the internet. DELEGATE to WEB_SEARCH for any substantive question.
- **rag mode**: User WANTS internal documents. DELEGATE to RETRIEVAL for any substantive question.
- **sql mode**: User WANTS database data. DELEGATE to SQL for any substantive question.
- **chat mode**: Auto mode - use your judgment.

ONLY respond directly (without delegating) when the message is:
- A simple messages
- A meta-question about the conversation itself
- An explicit request to stop

For ANY factual question, research request, or substantive inquiry: DELEGATE according to the mode.

## When to RESPOND directly
- Simple greetings and farewells.
- Acknowledgements ("OK", "Got it", "Thanks").
- Meta-requests about the conversation (change mode, explain what you did, stop).
- When workers have already gathered sufficient context and you need to synthesize.

## When to DELEGATE
- **Any substantive question** when mode is set (web/rag/sql)
- **One worker** when the question clearly maps to a single source
- **PLANNING** only for genuinely complex multi-part queries

## Handling Worker Results
- If worker succeeded with good data → synthesize results, cite sources, and respond.
- If partial results → evaluate whether to call another worker, ask user for clarification, or state limitations and return what you have.
- If error → report the error and recommend next steps.

## Response Composition
- State your decision briefly: whether you answered directly or delegated, which worker(s), and why.
- Summarize key findings first (1-3 sentences), then details, then sources.
- Include provenance (document title, source type, date) when using external data.

## Key Principles
- **RESPECT THE USER'S MODE CHOICE** - they selected it for a reason.
- Be transparent: if you make an assumption, label it.
- If an answer involves sensitive data, follow applicable privacy rules.
"""

ROUTING_PROMPT = """Analyze this interaction and decide what to do.

## User Message
{question}

## Context
- **Mode**: {mode} (USER'S EXPLICIT CHOICE - MUST be respected unless clearly irrelevant)
- **User Role**: {user_role} (IMPORTANT: SQL worker requires admin role)
- **Iteration**: {iteration}/{max_iterations}
- **Workers already used**: {workers_used}
{context_summary}

## MODE ENFORCEMENT RULES
- **web**: User explicitly wants web search. DELEGATE to WEB_SEARCH unless the question is purely conversational (greetings, thanks, meta-questions about the conversation).
- **rag**: User explicitly wants internal documents. DELEGATE to RETRIEVAL unless purely conversational.
- **sql**: User explicitly wants database queries. DELEGATE to SQL **ONLY IF user_role is admin**. If user_role is 'user', RESPOND with an error message that SQL mode is restricted to admins.
- **chat**: Auto mode - use your judgment, but still prefer delegation for factual/research questions.

## MEMORY COMMANDS (Any mode)
If the user asks to remember, recall, or forget something, DELEGATE to MEMORY worker:
- "Remember that..." / "Note that..." / "Keep in mind..." → DELEGATE to MEMORY
- "What do you know about me?" / "What have you remembered?" → DELEGATE to MEMORY
- "Forget that..." / "Delete the memory..." → DELEGATE to MEMORY

## Your Task
Think through:
1. **Intent**: What does the user actually want? (greeting, task, factual question, memory command, meta-request?)
2. **Is this a MEMORY command?**: Check for remember/recall/forget patterns FIRST.
3. **Is this purely conversational?**: Only "Hi", "Thanks", "Stop", etc. are purely conversational.
4. **Respect the MODE**: If user selected a specific mode (web/rag/sql), delegate to that worker for any substantive question.
5. **Have enough context?**: If workers already ran, is the gathered info sufficient?

## Output Format
ACTION: [DELEGATE|RESPOND|CLARIFY]
WORKER: [PLANNING|RETRIEVAL|WEB_SEARCH|SQL|MEMORY|NONE]
CONFIDENCE: [0.0-1.0]
REASONING: [Your thinking process - what intent you identified and why this action]
"""

RESPONSE_PROMPT = """Generate a final response to the user based on the gathered context.

## User's Question
{question}

## Gathered Context
{context}

## Response Guidelines
- Summarize key findings first (1-3 sentences)
- Provide supporting details
- Cite sources when applicable (document names, URLs, query context)
- Be concise but thorough
- If information is incomplete, acknowledge limitations
- Use markdown formatting for readability
- If you made assumptions, state them

## Your Response
"""


# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================

class RouterDecision(BaseModel):
    """Structured decision from the supervisor router."""
    action: str = Field(description="Action to take: DELEGATE, RESPOND, or CLARIFY")
    worker: Optional[str] = Field(default=None, description="Worker to delegate to if action is DELEGATE")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in decision")
    reasoning: str = Field(default="", description="Explanation for the decision")


# =============================================================================
# Supervisor Agent Class
# =============================================================================

class SupervisorAgent:
    """
    Supervisor Agent that coordinates the multi-agent workflow.
    
    The supervisor:
    1. Receives the user question
    2. Decides on actions (delegate, respond, clarify)
    3. Routes to appropriate workers
    4. Synthesizes final responses
    5. Handles human-in-the-loop
    """
    
    def __init__(self, config: Optional["AgentConfig"] = None):
        """
        Initialize the Supervisor Agent.
        
        Args:
            config: Optional agent configuration
        """
        self.config = config
        self._llm = None
    
    @property
    def llm(self):
        """Get the LLM model to use."""
        if self._llm is None:
            self._llm = form.SELECTED_MODEL.llm
        return self._llm
    
    def route(
        self,
        state: AgentState,
        memories_context: str = "",
    ) -> SupervisorDecision:
        """
        Make a routing decision based on current state.
        
        The supervisor (LLM) evaluates the user's message and decides:
        - Is this conversational? → Respond directly
        - Is this a task needing data? → Delegate to worker
        - Is this a meta-request? → Handle appropriately
        
        NO HARDCODED RULES - the LLM is the intelligent agent.
        
        Args:
            state: Current agent state
            memories_context: Optional long-term memories retrieved from store
        
        Returns:
            SupervisorDecision with the action to take
        """
        log_info("Supervisor making routing decision")
        if memories_context:
            log_debug(f"Using long-term memories: {len(memories_context)} chars")
        
        # Check termination conditions (these are system limits, not routing logic)
        if is_execution_complete(state):
            return SupervisorDecision(
                action=SupervisorAction.RESPOND,
                reasoning="Execution already complete",
            )
        
        if has_exceeded_iterations(state):
            return SupervisorDecision(
                action=SupervisorAction.RESPOND,
                reasoning="Maximum iterations reached, generating response with available context",
            )
        
        # Gather state for LLM decision
        question = state.get("original_question", "")
        # Also track the latest HumanMessage content for debugging mismatches.
        latest_human = ""
        try:
            msgs = state.get("messages") or []
            for m in reversed(msgs):
                if isinstance(m, HumanMessage):
                    latest_human = str(m.content or "")
                    break
        except Exception:
            latest_human = ""

        log_info(
            "Supervisor.route input: "
            f"original_question={str(question)[:120]!r} latest_human={str(latest_human)[:120]!r} "
            f"mode={state.get('mode', 'chat')!r}"
        )
        mode = state.get("mode", "chat")
        iteration = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)
        worker_results = state.get("worker_results") or []
        workers_used = [r.worker_type.value for r in worker_results]
        context = get_gathered_context(state)
        
        # Get user role from metadata (passed from config)
        metadata = state.get("metadata") or {}
        user_role = metadata.get("user_role", "user")
        
        # Build context summary for LLM
        context_summary = ""
        if context:
            context_summary = f"\n## Context gathered from workers:\n{context[:MAX_CONTEXT_LENGTH]}"
        
        # Add long-term memories if available
        if memories_context:
            context_summary = f"\n{memories_context}\n{context_summary}"
        
        # Add SQL schema context if in SQL mode
        sql_schema_info = ""
        if mode == "sql":
            sql_schema_info = self._get_sql_schema_summary(state)
        
        # Let the LLM (the actual agent) decide
        routing_prompt = ROUTING_PROMPT.format(
            question=question,
            mode=mode,
            user_role=user_role,
            iteration=iteration,
            max_iterations=max_iterations,
            workers_used=", ".join(workers_used) if workers_used else "None yet",
            context_summary=context_summary + sql_schema_info,
        )
        
        try:
            decision = self._get_routing_decision(routing_prompt)
            
            # SECURITY CHECK: Block SQL delegation for non-admin users
            if decision.next_worker == WorkerType.SQL and user_role != "admin":
                log_warning(f"Blocked SQL delegation for non-admin user (role={user_role})")
                return SupervisorDecision(
                    action=SupervisorAction.RESPOND,
                    reasoning="SQL queries are restricted to admin users. Please contact an administrator for database access.",
                )
            
            log_success(f"Supervisor decided: {decision.action.value} -> {decision.next_worker}")
            return decision
            
        except Exception as e:
            log_error(f"Routing decision failed: {e}")
            return SupervisorDecision(
                action=SupervisorAction.RESPOND,
                reasoning=f"Routing failed ({e}), attempting response with available context",
            )
    
    def _get_routing_decision(self, prompt: str) -> SupervisorDecision:
        """
        Get a routing decision from the LLM.
        
        Args:
            prompt: The routing prompt
        
        Returns:
            Parsed SupervisorDecision
        """
        messages = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        
        log_debug(f"Supervisor routing prompt: {prompt[:500]}...")
        
        response = self.llm.invoke(messages)
        response_text = str(response.content) if hasattr(response, "content") else str(response)
        
        log_info(f"Supervisor LLM response: {response_text[:500]}...")
        
        return self._parse_decision(response_text)
    
    def _parse_decision(self, response: str) -> SupervisorDecision:
        """
        Parse the LLM response into a SupervisorDecision.
        
        Args:
            response: Raw LLM response text
        
        Returns:
            Parsed SupervisorDecision
        """
        lines = response.strip().split("\n")
        
        action = SupervisorAction.RESPOND
        worker = None
        confidence = 1.0
        reasoning = ""
        
        for line in lines:
            line_upper = line.upper().strip()
            
            if line_upper.startswith("ACTION:"):
                value = line.split(":", 1)[1].strip().upper()
                action = self._parse_action(value)
            
            elif line_upper.startswith("WORKER:"):
                value = line.split(":", 1)[1].strip().upper()
                worker = self._parse_worker(value)
            
            elif line_upper.startswith("CONFIDENCE:"):
                try:
                    value = line.split(":", 1)[1].strip()
                    confidence = float(value)
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, IndexError):
                    pass
            
            elif line_upper.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
        
        return SupervisorDecision(
            action=action,
            next_worker=worker,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def _parse_action(self, value: str) -> SupervisorAction:
        """Parse action string to enum."""
        action_map = {
            "DELEGATE": SupervisorAction.DELEGATE,
            "RESPOND": SupervisorAction.RESPOND,
            "CLARIFY": SupervisorAction.CLARIFY,
            "WAIT_HUMAN": SupervisorAction.WAIT_HUMAN,
            # REFLECT is deprecated - supervisor evaluates results naturally
        }
        return action_map.get(value, SupervisorAction.RESPOND)
    
    def _parse_worker(self, value: str) -> Optional[WorkerType]:
        """Parse worker string to enum."""
        if not value or value == "NONE":
            return None
        
        worker_map = {
            "PLANNING": WorkerType.PLANNING,
            "RETRIEVAL": WorkerType.RETRIEVAL,
            "WEB_SEARCH": WorkerType.WEB_SEARCH,
            "WEB": WorkerType.WEB_SEARCH,
            "SQL": WorkerType.SQL,
            "MEMORY": WorkerType.MEMORY,
        }
        return worker_map.get(value)
    
    def _get_sql_schema_summary(self, state: AgentState) -> str:
        """
        Get a brief SQL schema summary for supervisor context.
        
        This gives the supervisor awareness of available tables
        so it can make better routing decisions for SQL mode.
        
        Args:
            state: Current agent state
            
        Returns:
            Schema summary string
        """
        # Check for cached schema context in state
        cached = state.get("sql_schema_context")
        if cached:
            return f"\n\n## Available Database Tables:\n{cached}"
        
        try:
            from backend.application.services.sql_schema_service import sql_schema_service
            overview = sql_schema_service.get_schema_overview()
            return f"\n\n## Available Database Tables:\n{overview}"
        except Exception as e:
            log_warning(f"Could not get SQL schema for supervisor: {e}")
            return ""
    
    def generate_response(self, state: AgentState) -> str:
        """
        Generate the final response based on gathered context.
        
        Args:
            state: Current agent state with gathered context
        
        Returns:
            Final response string
        """
        log_info("Supervisor generating final response")
        
        question = state.get("original_question", "")
        context = get_gathered_context(state)
        
        log_debug(f"Generating response for question: {question[:200]}")
        log_debug(f"Context available: {len(context)} chars")
        
        # Check if we can answer directly without context
        if not context:
            # Simple question, try direct answer
            log_info("No context gathered - generating direct response")
            prompt = f"Answer this question concisely: {question}"
            messages = [
                SystemMessage(content="You are a helpful assistant. Answer questions directly and accurately."),
                HumanMessage(content=prompt),
            ]
        else:
            # Use gathered context
            log_info(f"Using gathered context ({len(context)} chars) to generate response")
            prompt = RESPONSE_PROMPT.format(
                question=question,
                context=context,
            )
            messages = [
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        
        try:
            response = self.llm.invoke(messages)
            response_text = str(response.content) if hasattr(response, "content") else str(response)
            log_success(f"Supervisor generated response ({len(response_text)} chars): {response_text[:200]}...")
            return response_text.strip()
        except Exception as e:
            log_error(f"Response generation failed: {e}")
            return f"I apologize, but I encountered an error generating a response: {str(e)}"
    
    def stream_response(self, state: AgentState) -> Iterator[str]:
        """
        Stream the final response token by token.
        
        Args:
            state: Current agent state
        
        Yields:
            Response tokens
        """
        question = state.get("original_question", "")
        context = get_gathered_context(state)
        
        if not context:
            prompt = f"Answer this question concisely: {question}"
            messages = [
                SystemMessage(content="You are a helpful assistant. Answer questions directly and accurately."),
                HumanMessage(content=prompt),
            ]
        else:
            prompt = RESPONSE_PROMPT.format(
                question=question,
                context=context,
            )
            messages = [
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        
        try:
            for chunk in self.llm.stream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield str(chunk.content)
        except Exception as e:
            log_error(f"Response streaming failed: {e}")
            yield f"Error: {str(e)}"
    
    def request_clarification(self, state: AgentState) -> HumanInterrupt:
        """
        Create a clarification request for the user.
        
        Args:
            state: Current agent state
        
        Returns:
            HumanInterrupt for clarification
        """
        question = state.get("original_question", "")
        
        # Generate clarification message
        prompt = f"""The user asked: {question}

This question needs clarification. Generate a brief, friendly question to ask the user
for more specific information. Focus on what's most ambiguous or unclear.

Respond with just the clarification question."""
        
        messages = [
            SystemMessage(content="You are a helpful assistant that asks clarifying questions."),
            HumanMessage(content=prompt),
        ]
        
        try:
            response = self.llm.invoke(messages)
            clarification = str(response.content).strip()
        except Exception:
            clarification = "Could you please provide more details about your question?"
        
        return HumanInterrupt(
            interrupt_type=HumanInterruptType.CLARIFICATION,
            message=clarification,
            context={"original_question": question},
        )
    
    def get_mode_hint(self, mode: str) -> Optional[WorkerType]:
        """
        Get a hint for the primary worker based on mode.
        
        This is just a hint - the LLM supervisor makes the final decision.
        
        Args:
            mode: Execution mode
        
        Returns:
            Suggested WorkerType (or None for chat mode)
        """
        mode_workers = {
            "rag": WorkerType.RETRIEVAL,
            "web": WorkerType.WEB_SEARCH,
            "sql": WorkerType.SQL,
            "chat": None,  # LLM decides based on content
        }
        return mode_workers.get(mode)


def create_supervisor(config: Optional["AgentConfig"] = None) -> SupervisorAgent:
    """Factory function to create a SupervisorAgent."""
    return SupervisorAgent(config=config)
