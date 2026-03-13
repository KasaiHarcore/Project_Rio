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
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from infrastructure.llm import form
from core.settings import DEFAULT_MAX_ITERATIONS, MAX_CONTEXT_LENGTH, MAX_RESPONSE_LENGTH
from utils.log import log_debug, log_error, log_info, log_success, log_warning
from workflows.persona import get_persona
from workflows.state import (
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
    from core.settings import AgentConfig

SUPERVISOR_SYSTEM_PROMPT = """I am the Supervisor agent — the central decision-maker in a multi-agent system. I assist Sensei with their studies, research, and daily tasks.

## My Role
- I refer to the user as **Sensei** — always.
- I analyze Sensei's messages and decide the best course of action.
- I either RESPOND directly or DELEGATE to a specialized worker.
- When delegating, I select the minimum set of worker(s) needed.
- When synthesizing, I combine worker outputs into a single clear, factual answer for Sensei.
- I am provenance-aware — I cite sources and origin of facts when relevant.

## Workers Available
1. **PLANNING** — designs multi-step execution plans for genuinely complex, multi-part queries.
2. **RETRIEVAL** — searches internal knowledge bases / documents / RAG store.
3. **WEB_SEARCH** — searches the internet for current information.
4. **SQL** — queries the application database with intelligent safety controls:
   - **READ operations** (SELECT): Executed automatically for quick data retrieval
   - **WRITE operations** (INSERT/UPDATE/DELETE): Require Sensei's approval via Human-in-the-Loop
   - The SQL worker has schema awareness and classifies operations by danger level
   - **ADMIN ONLY** — only delegate to SQL if user_role is admin
5. **MEMORY** — manages long-term memory about Sensei:
   - **STORE**: When Sensei says "remember that…", "keep in mind…"
   - **RECALL**: When Sensei asks "what do you know about me?"
   - **FORGET**: When Sensei says "forget that…", "delete the memory about…"
6. **NOTE** — extracts important notes, key takeaways, and TODO action items:
   - Triggered when the conversation produces actionable insights, study plans, or structured steps
   - Creates visible sidebar notes that help Sensei track important information
   - Use when the answer involves a roadmap, checklist, study plan, or important facts worth pinning
   - NOT for simple greetings or trivial answers — only when there is real value to capture
7. **MISSION** — extracts trackable missions / goals from the conversation:
   - Triggered when Sensei explicitly asks to create a task, or when the conversation produces a clear goal
   - Creates persistent missions on the Mission Page with optional step checklists
   - Use when Sensei says "create a task", "add a mission", "I need to do…", "my goal is…"
   - Also use when a study plan or project roadmap emerges that should be tracked long-term
   - NOT for transient notes or simple Q&A — only for actionable, trackable goals

## CRITICAL: Respecting Sensei's Mode Selection
Sensei has explicitly selected a MODE (rag/web/sql/chat). This is their INTENTIONAL CHOICE:
- **web mode**: Sensei WANTS information from the internet. DELEGATE to WEB_SEARCH for any substantive question.
- **rag mode**: Sensei WANTS internal documents. DELEGATE to RETRIEVAL for any substantive question.
- **sql mode**: Sensei WANTS database data. DELEGATE to SQL for any substantive question.
- **chat mode**: Auto mode — use my judgment.

I ONLY respond directly (without delegating) when the message is:
- A simple greeting or farewell
- A meta-question about the conversation itself
- An explicit request to stop

For ANY factual question, research request, or substantive inquiry: I DELEGATE according to the mode.

## When to RESPOND Directly
- Simple greetings and farewells.
- Acknowledgements ("OK", "Got it", "Thanks").
- Meta-requests about the conversation (change mode, explain what I did, stop).
- When workers have already gathered sufficient context and I need to synthesize.

## When to DELEGATE
- **Any substantive question** when a mode is set (web/rag/sql)
- **One worker** when the question clearly maps to a single source
- **PLANNING** only for genuinely complex multi-part queries

## Handling Worker Results
- If worker succeeded with good data → I synthesize results, cite sources, and respond.
- If partial results → I evaluate whether to call another worker, ask Sensei for clarification, or state limitations and return what I have.
- If error → I report the error honestly and recommend next steps.

## Response Composition
- I summarize key findings first (1-3 sentences), then details, then sources.
- I include provenance (document title, source type, date) when using external data.
- I use markdown formatting for readability.
- I write in a neutral, clear, factual tone.
- NOTE: My output will be rewritten into the character's voice by a downstream filter.
  I should focus on accuracy and completeness, not personality.

## Key Principles
- **RESPECT Sensei's MODE CHOICE** — they selected it for a reason.
- Be transparent: if I make an assumption, I say so.
- If an answer involves sensitive data, follow applicable privacy rules.
- Task quality and factual accuracy come first.
"""

ROUTING_PROMPT = """I need to analyze Sensei's message and decide the best course of action.

## Sensei's Message
{question}

## Context
- **Mode**: {mode} (Sensei's explicit choice — MUST be respected unless clearly irrelevant)
- **User Role**: {user_role} (IMPORTANT: SQL worker requires admin role)
- **Iteration**: {iteration}/{max_iterations}
- **Workers already used**: {workers_used}
{context_summary}

## MODE ENFORCEMENT RULES
- **web**: Sensei wants web search. DELEGATE to WEB_SEARCH unless the message is purely conversational.
- **rag**: Sensei wants internal documents. DELEGATE to RETRIEVAL unless purely conversational.
- **sql**: Sensei wants database queries. DELEGATE to SQL **ONLY IF user_role is admin**. If user_role is 'user', RESPOND explaining SQL mode is restricted to admins.
- **chat**: Auto mode — I use my judgment, but still prefer delegation for factual/research questions.

## MEMORY COMMANDS (Any mode)
If Sensei asks to remember, recall, or forget something, DELEGATE to MEMORY worker:
- "Remember that…" / "Note that…" / "Keep in mind…" → DELEGATE to MEMORY
- "What do you know about me?" / "What have you remembered?" → DELEGATE to MEMORY
- "Forget that…" / "Delete the memory…" → DELEGATE to MEMORY

## NOTE EXTRACTION (Any mode, after workers have gathered context)
If the conversation produced actionable insights, study plans, TODO steps, or structured checklists:
- DELEGATE to NOTE worker **after** the primary worker has already gathered context
- Only use NOTE when there is substantive, structured content worth surfacing as a sidebar note
- Do NOT use NOTE for simple Q&A, greetings, or trivial exchanges

## MISSION CREATION (Any mode)
If Sensei explicitly asks to create a task/mission, or the conversation produces a clear trackable goal:
- "Create a task to…" / "Add a mission for…" / "I need to…" / "My goal is…" → DELEGATE to MISSION
- Also DELEGATE to MISSION when a study plan, project roadmap, or set of milestones emerges
- MISSION creates **persistent** items on the Mission Page — use for long-term goals, not transient info
- Do NOT use MISSION for simple Q&A or trivial requests

## My Task
I will think through:
1. **Intent**: What does Sensei actually want? (greeting, task, factual question, memory command, mission creation, meta-request?)
2. **Is this a MEMORY command?**: Check for remember/recall/forget patterns FIRST.
3. **Is this a MISSION request?**: Check for "create task", "add mission", explicit goal-setting.
4. **Is this purely conversational?**: Only "Hi", "Thanks", "Stop", etc. are purely conversational.
5. **Respect the MODE**: If Sensei selected a specific mode (web/rag/sql), I delegate to that worker for any substantive question.
6. **Have enough context?**: If workers already ran, is the gathered info sufficient?

## Output Format
ACTION: [DELEGATE|RESPOND|CLARIFY]
WORKER: [PLANNING|RETRIEVAL|WEB_SEARCH|SQL|MEMORY|NOTE|MISSION|NONE]
CONFIDENCE: [0.0-1.0]
REASONING: [My thinking process — what intent I identified and why this action]
"""

RESPONSE_PROMPT = """I will now generate a final answer for Sensei based on the gathered context.

## Sensei's Question
{question}

## Gathered Context
{context}

## My Response Guidelines
- I summarize key findings first (1-3 sentences), then supporting details, then sources.
- I cite sources when applicable (document names, URLs, query context).
- I am concise but thorough — Sensei's time matters.
- If information is incomplete, I acknowledge limitations honestly.
- I use markdown formatting for readability.
- I write in a neutral, clear, factual tone.
- I refer to the user as Sensei where it flows naturally.
- NOTE: My output will be rewritten into the character's voice downstream.
  I focus on accuracy and completeness, not personality.

## My Response
"""

class RouterDecision(BaseModel):
    """Structured decision from the supervisor router."""
    action: str = Field(description="Action to take: DELEGATE, RESPOND, or CLARIFY")
    worker: Optional[str] = Field(default=None, description="Worker to delegate to if action is DELEGATE")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in decision")
    reasoning: str = Field(default="", description="Explanation for the decision")

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

        # Resolve persona only for user_address and fallback_nudge
        character_id = config.character if config else None
        self._persona = get_persona(character_id)

    @property
    def _system_prompt(self) -> str:
        return SUPERVISOR_SYSTEM_PROMPT

    @property
    def _routing_prompt_tpl(self) -> str:
        """Routing prompt — has {question}, {mode}, etc. placeholders."""
        return ROUTING_PROMPT

    @property
    def _response_prompt_tpl(self) -> str:
        """Response prompt — has {question}, {context} placeholders."""
        return RESPONSE_PROMPT

    @property
    def _direct_system_prompt(self) -> str:
        """System prompt for direct (no-context) responses."""
        return (
            "I am a helpful assistant. I answer Sensei's questions directly, "
            "accurately, and in a neutral, clear tone. I refer to the user as "
            "Sensei where it flows naturally. My output will be rewritten into "
            "the character's voice downstream, so I focus on accuracy."
        )

    @property
    def _clarification_system_prompt(self) -> str:
        return (
            "I am a helpful assistant. I call the user Sensei. "
            "I need to ask clarifying questions in a clear, neutral manner."
        )
    
    # Maximum number of recent history messages to include in LLM calls.
    # This prevents context overflow while giving the LLM conversational memory.
    MAX_HISTORY_MESSAGES = 20

    @property
    def llm(self):
        """Get the LLM model to use."""
        if self._llm is None:
            self._llm = form.SELECTED_MODEL.llm
        return self._llm

    def _get_history_messages(
        self,
        state: "AgentState",
        max_messages: int = 20,
    ) -> List[BaseMessage]:
        """Extract recent conversation history from state for LLM context.

        Returns the most recent *max_messages* messages **excluding** the
        current HumanMessage (which is already represented in the prompts).
        This gives the LLM awareness of the ongoing conversation.
        """
        all_msgs: List[BaseMessage] = list(state.get("messages") or [])
        if not all_msgs:
            return []

        # The last message is the current user question (added by create_initial_state).
        # We want everything *before* it as history context.
        history = all_msgs[:-1] if all_msgs else []

        # Keep only the tail to respect context-window limits.
        if len(history) > max_messages:
            history = history[-max_messages:]

        return history
    
    def route(
        self,
        state: AgentState,
        memories_context: str = "",
        emotional_ctx: Optional[Dict[str, str]] = None,
    ) -> SupervisorDecision:
        """
        Make a routing decision based on current state.

        The supervisor (LLM) evaluates the user's message and decides:
        - Is this conversational? → Respond directly
        - Is this a task needing data? → Delegate to worker
        - Is this a meta-request? → Handle appropriately

        Args:
            state: Current agent state
            memories_context: Optional long-term memories retrieved from store
            emotional_ctx: Optional emotional context (ignored here, kept for API compat)

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
        routing_prompt = self._routing_prompt_tpl.format(
            question=question,
            mode=mode,
            user_role=user_role,
            iteration=iteration,
            max_iterations=max_iterations,
            workers_used=", ".join(workers_used) if workers_used else "None yet",
            context_summary=context_summary + sql_schema_info
        )
        
        try:
            decision = self._get_routing_decision(routing_prompt, state=state)
            
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
    
    def _get_routing_decision(
        self,
        prompt: str,
        state: Optional["AgentState"] = None,
    ) -> SupervisorDecision:
        """
        Get a routing decision from the LLM.
        
        Args:
            prompt: The routing prompt
            state: Optional agent state for injecting conversation history
        
        Returns:
            Parsed SupervisorDecision
        """
        messages: List[BaseMessage] = [SystemMessage(content=self._system_prompt)]

        # Inject recent conversation history so the LLM is aware of prior turns.
        if state is not None:
            history = self._get_history_messages(state, self.MAX_HISTORY_MESSAGES)
            if history:
                messages.extend(history)

        messages.append(HumanMessage(content=prompt))
        
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
            "NOTE": WorkerType.NOTE,
            "MISSION": WorkerType.MISSION,
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
            from services.sql_schema_service import sql_schema_service
            overview = sql_schema_service.get_schema_overview()
            return f"\n\n## Available Database Tables:\n{overview}"
        except Exception as e:
            log_warning(f"Could not get SQL schema for supervisor: {e}")
            return ""
    
    def generate_response(
        self,
        state: AgentState,
        memories_context: str = "",
        emotional_ctx: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate the final response based on gathered context.

        The output is a neutral, factual synthesis. Character voice is
        applied later by the PersonaFilter.

        Args:
            state: Current agent state with gathered context
            memories_context: Long-term memories retrieved from PostgresStore
            emotional_ctx: Optional emotional context (ignored, kept for API compat)

        Returns:
            Final response string (neutral tone)
        """
        log_info("Supervisor generating final response (neutral)")
        
        question = state.get("original_question", "")
        context = get_gathered_context(state)
        
        # Prepend long-term memories to context so the LLM can reference them.
        if memories_context:
            context = f"{memories_context}\n\n{context}" if context else memories_context
        
        log_debug(f"Generating response for question: {question[:200]}")
        log_debug(f"Context available: {len(context)} chars")
        
        # Retrieve conversation history for continuity.
        history = self._get_history_messages(state, self.MAX_HISTORY_MESSAGES)
        
        # Check if we can answer directly without context
        if not context:
            # Simple question, try direct answer
            log_info("No context gathered - generating direct response")
            prompt = f"Answer this question concisely: {question}"
            messages: List[BaseMessage] = [
                SystemMessage(content=self._direct_system_prompt),
            ]
            if history:
                messages.extend(history)
                log_debug(f"Injected {len(history)} history messages into direct response")
            messages.append(HumanMessage(content=prompt))
        else:
            # Use gathered context
            log_info(f"Using gathered context ({len(context)} chars) to generate response")
            prompt = self._response_prompt_tpl.format(
                question=question,
                context=context,
            )
            messages: List[BaseMessage] = [
                SystemMessage(content=self._system_prompt),
            ]
            if history:
                messages.extend(history)
                log_debug(f"Injected {len(history)} history messages into context response")
            messages.append(HumanMessage(content=prompt))
        
        try:
            response = self.llm.invoke(messages)
            response_text = str(response.content) if hasattr(response, "content") else str(response)
            response_text = response_text.strip()
            if len(response_text) > MAX_RESPONSE_LENGTH:
                log_warning(f"Response truncated: {len(response_text)} > {MAX_RESPONSE_LENGTH} chars")
                response_text = response_text[:MAX_RESPONSE_LENGTH]
            log_success(f"Supervisor generated response ({len(response_text)} chars): {response_text[:200]}...")
            return response_text
        except Exception as e:
            log_error(f"Response generation failed: {e}")
            return f"I apologize, but I encountered an error generating a response: {str(e)}"
    
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
        prompt = f"""Sensei asked: {question}

This question needs clarification. I will generate a brief, clear question to ask Sensei
for more specific information. I focus on what's most ambiguous or unclear.
I keep it concise and neutral.

Respond with just the clarification question."""
        
        messages = [
            SystemMessage(content=self._clarification_system_prompt),
            HumanMessage(content=prompt),
        ]
        
        try:
            response = self.llm.invoke(messages)
            clarification = str(response.content).strip()
        except Exception:
            clarification = self._persona.fallback_nudge.format(**self._persona.to_vars())
        
        return HumanInterrupt(
            interrupt_type=HumanInterruptType.CLARIFICATION,
            message=clarification,
            context={"original_question": question},
        )
    
