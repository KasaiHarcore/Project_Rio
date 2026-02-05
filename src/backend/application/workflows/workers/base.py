"""
Base Worker Classes for Multi-agent Architecture.

This module defines the abstract base class for all worker agents.
Workers are specialized, single-task agents that:
- Receive specific tasks from the supervisor
- Execute their specialized function
- Return structured results
- Support streaming and interruption

Workers do NOT make routing decisions - that's the supervisor's job.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from backend.infrastructure.integrations.llm import form
from backend.utils.log import log_debug, log_error, log_info, log_success, log_warning
from backend.application.workflows.state import (
    AgentState,
    WorkerResult,
    WorkerType,
    ExecutionPlan,
)

if TYPE_CHECKING:
    from backend.core.settings import AgentConfig


class BaseWorker(ABC):
    """
    Abstract base class for all worker agents.
    
    Workers are specialized agents that perform a single, focused task.
    They receive context from the supervisor and return structured results.
    
    Subclasses must implement:
    - worker_type: The type of worker (for identification)
    - _execute: The core execution logic
    """
    
    @property
    @abstractmethod
    def worker_type(self) -> WorkerType:
        """Return the type of this worker."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this worker."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this worker does."""
        raise NotImplementedError
    
    @property
    def system_prompt(self) -> str:
        """System prompt for the worker LLM."""
        return f"""You are {self.name}, a specialized assistant.
Your role: {self.description}

Guidelines:
- Focus only on your specific task
- Be concise and accurate
- Cite sources when applicable
- If you cannot complete the task, explain why clearly
"""
    
    def __init__(self, config: Optional["AgentConfig"] = None):
        """
        Initialize the worker.
        
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
    
    def execute(self, state: AgentState) -> WorkerResult:
        """
        Execute the worker task and return a structured result.
        
        This is the main entry point called by the workflow graph.
        It handles timing, error handling, and result formatting.
        
        Args:
            state: Current agent state
        
        Returns:
            WorkerResult with execution outcome
        """
        start_time = time.time()
        log_info(f"Starting {self.name} worker execution")
        
        try:
            result = self._execute(state)
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Ensure we have a WorkerResult
            if isinstance(result, WorkerResult):
                result.execution_time_ms = execution_time_ms
                log_success(f"{self.name} completed in {execution_time_ms}ms")
                return result
            
            # Handle string result (backwards compatibility)
            if isinstance(result, str):
                log_success(f"{self.name} completed in {execution_time_ms}ms")
                return WorkerResult(
                    worker_type=self.worker_type,
                    success=True,
                    content=result,
                    execution_time_ms=execution_time_ms,
                )
            
            # Unexpected result type
            log_warning(f"{self.name} returned unexpected type: {type(result)}")
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content=str(result),
                execution_time_ms=execution_time_ms,
            )
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            log_error(f"{self.name} failed after {execution_time_ms}ms: {error_msg}")
            
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=error_msg,
                execution_time_ms=execution_time_ms,
            )
    
    @abstractmethod
    def _execute(self, state: AgentState) -> WorkerResult:
        """
        Core execution logic to be implemented by subclasses.
        
        Args:
            state: Current agent state
        
        Returns:
            WorkerResult or string content
        """
        raise NotImplementedError
    
    def stream(self, state: AgentState) -> Iterator[str]:
        """
        Stream execution output token by token.
        
        Default implementation runs _execute and yields the result.
        Subclasses can override for true streaming.
        
        Args:
            state: Current agent state
        
        Yields:
            String tokens
        """
        result = self.execute(state)
        if result.content:
            yield result.content
    
    def _call_llm(
        self,
        *,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Helper to call the LLM with a prompt.
        
        Args:
            user_prompt: The user message
            system_prompt: Optional system prompt override
            context: Optional context to prepend
        
        Returns:
            LLM response text
        """
        effective_system = system_prompt or self.system_prompt
        
        if context:
            user_prompt = f"Context:\n{context}\n\n{user_prompt}"
        
        messages: List[BaseMessage] = [
            SystemMessage(content=effective_system),
            HumanMessage(content=user_prompt),
        ]
        
        response = self.llm.invoke(messages)
        
        if isinstance(response, AIMessage):
            return str(response.content or "")
        return str(response)
    
    def _stream_llm(
        self,
        *,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Helper to stream LLM output.
        
        Args:
            user_prompt: The user message
            system_prompt: Optional system prompt override
            context: Optional context to prepend
        
        Yields:
            String tokens
        """
        effective_system = system_prompt or self.system_prompt
        
        if context:
            user_prompt = f"Context:\n{context}\n\n{user_prompt}"
        
        messages: List[BaseMessage] = [
            SystemMessage(content=effective_system),
            HumanMessage(content=user_prompt),
        ]
        
        for chunk in self.llm.stream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield str(chunk.content)
    
    def get_question(self, state: AgentState) -> str:
        """Extract the question from state."""
        return state.get("original_question") or ""
    
    def get_context(self, state: AgentState) -> str:
        """Extract gathered context from state."""
        return state.get("gathered_context") or ""
    
    def get_last_decision_reasoning(self, state: AgentState) -> str:
        """Get the reasoning from the last supervisor decision."""
        decisions = state.get("supervisor_decisions") or []
        if decisions:
            return decisions[-1].reasoning
        return ""
