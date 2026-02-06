"""
Agent Service - Multi-Agent Supervisor-Worker Orchestration

This service provides the interface between the API layer and the multi-agent
workflow system. It handles:
- Workflow execution (sync and streaming)
- Configuration management
- Statistics collection and reporting
"""

from typing import Optional, List, Dict, Any, Iterator

from backend.utils.log import log_info, log_success, log_error, log_warning
from backend.infrastructure.integrations.llm import form
from backend.core.settings import AgentConfig
from backend.application.workflows import run_workflow, stream_workflow


class AgentService:
    """
    Service layer for executing multi-agent workflows.
    
    The supervisor-worker architecture handles:
    - Automatic routing to appropriate workers
    - Tool selection and execution
    - Response synthesis
    
    This service manages:
    - Model initialization
    - Configuration validation
    - Statistics collection
    """
    
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

        log_info(f"Executing workflow for question: {question[:100]}...")

        try:
            result = run_workflow(
                question=question,
                config=config,
                history=history,
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                checkpoint_ns=checkpoint_ns,
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
        user_id: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream a query and yield events from the multi-agent workflow.
        
        Event types:
        - token: Streaming token from LLM
        - worker_start: Worker execution started
        - worker_end: Worker execution completed
        - supervisor: Supervisor decision
        - final: Final response with stats
        - error: Error occurred
        """
        if config is None:
            config = AgentConfig()

        if config.model_name:
            form.set_model(config.model_name)

        if not form.SELECTED_MODEL:
            raise ValueError("No model is registered. Check configuration")

        if not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()

        log_info(f"Streaming workflow for question: {question[:100]}...")

        for event in stream_workflow(
            question=question,
            config=config,
            history=history,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=checkpoint_ns,
            user_id=user_id,
        ):
            yield event
