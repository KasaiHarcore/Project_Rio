"""
Planning Worker - Creates execution plans for complex queries.

The Planning Worker analyzes user questions and creates structured
execution plans that guide the supervisor in delegating to other workers.

Responsibilities:
- Analyze the complexity of the user's question
- Identify which workers/tools are needed
- Create a step-by-step execution plan
- Estimate complexity and resource requirements
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.workflows.state import (
    AgentState,
    ExecutionPlan,
    WorkerResult,
    WorkerType,
)
from backend.workflows.workers.base import BaseWorker
from backend.utils.log import log_info, log_debug


PLANNING_SYSTEM_PROMPT = """You are a Planning Assistant that creates execution plans for answering user questions.

Your job is to analyze the user's question and create a clear, step-by-step plan.

Available Workers:
1. RETRIEVAL - Search internal knowledge base/documents for relevant information
2. WEB_SEARCH - Search the web for current information, news, or facts
3. SQL - Query the application database for structured data (users, threads, messages, etc.)

Guidelines:
- Analyze what information is needed to answer the question
- Identify which worker(s) should be used
- Create concrete, actionable steps
- Consider the order of operations (some steps may depend on others)
- Keep plans focused and minimal - don't over-engineer

Output Format:
COMPLEXITY: [simple|moderate|complex]

WORKERS_NEEDED: [comma-separated list of worker types]

REASONING:
[Brief explanation of why this plan was chosen]

PLAN:
1. [Step 1 description] -> WORKER: [worker_type]
2. [Step 2 description] -> WORKER: [worker_type]
...

NOTES:
[Any special considerations or dependencies between steps]
"""


class PlanningWorker(BaseWorker):
    """
    Planning Worker creates execution plans for complex queries.
    
    The plan helps the supervisor determine which workers to invoke
    and in what order to best answer the user's question.
    """
    
    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.PLANNING
    
    @property
    def name(self) -> str:
        return "Planning Worker"
    
    @property
    def description(self) -> str:
        return "Analyzes questions and creates structured execution plans"
    
    @property
    def system_prompt(self) -> str:
        return PLANNING_SYSTEM_PROMPT
    
    def _execute(self, state: AgentState) -> WorkerResult:
        """
        Create an execution plan for the user's question.
        
        Args:
            state: Current agent state
        
        Returns:
            WorkerResult containing the execution plan
        """
        question = self.get_question(state)
        mode = state.get("mode", "chat")
        
        log_info(f"Planning for question: {question[:100]}... (mode={mode})")
        
        # Build the planning prompt
        user_prompt = self._build_planning_prompt(question, mode, state)
        
        # Call LLM to generate the plan
        plan_text = self._call_llm(user_prompt=user_prompt)
        
        # Parse the plan
        execution_plan = self._parse_plan(plan_text)
        
        return WorkerResult(
            worker_type=self.worker_type,
            success=True,
            content=plan_text,
            metadata={
                "execution_plan": execution_plan.to_dict(),
                "complexity": execution_plan.complexity,
                "estimated_workers": [w.value for w in execution_plan.estimated_workers],
            },
        )
    
    def _build_planning_prompt(
        self,
        question: str,
        mode: str,
        state: AgentState,
    ) -> str:
        """Build the prompt for the planning LLM."""
        parts = [f"User Question: {question}"]
        
        # Add mode-specific guidance
        mode_guidance = self._get_mode_guidance(mode)
        if mode_guidance:
            parts.append(f"\nMode Guidance ({mode}):\n{mode_guidance}")
        
        # Add context if available
        context = self.get_context(state)
        if context:
            parts.append(f"\nAvailable Context:\n{context[:1000]}...")
        
        # Add previous decisions if any
        decisions = state.get("supervisor_decisions") or []
        if decisions:
            decision_summary = "\n".join([
                f"- {d.action.value}: {d.reasoning[:100]}"
                for d in decisions[-3:]
            ])
            parts.append(f"\nPrevious Decisions:\n{decision_summary}")
        
        parts.append("\nCreate an execution plan to answer this question.")
        
        return "\n".join(parts)
    
    def _get_mode_guidance(self, mode: str) -> str:
        """Get mode-specific planning guidance."""
        guidance = {
            "rag": (
                "Focus on RETRIEVAL worker for searching internal documents. "
                "Web search should only be used if internal docs are insufficient."
            ),
            "web": (
                "Focus on WEB_SEARCH worker for finding current information. "
                "Prefer authoritative sources and verify time-sensitive facts."
            ),
            "chat": (
                "Determine if the question needs internal docs, web search, or "
                "can be answered directly. Choose the minimal set of workers needed."
            ),
            "sql": (
                "Focus on SQL worker for querying structured application data. "
                "Be mindful of data sensitivity and only query what's needed."
            ),
        }
        return guidance.get(mode, "")
    
    def _parse_plan(self, plan_text: str) -> ExecutionPlan:
        """Parse the LLM output into a structured ExecutionPlan."""
        lines = plan_text.strip().split("\n")
        
        complexity = "simple"
        workers_needed: List[WorkerType] = []
        reasoning = ""
        steps: List[Dict[str, Any]] = []
        
        current_section = None
        reasoning_lines: List[str] = []
        
        for line in lines:
            line_stripped = line.strip()
            line_upper = line_stripped.upper()
            
            # Parse complexity
            if line_upper.startswith("COMPLEXITY:"):
                value = line_stripped.split(":", 1)[1].strip().lower()
                if value in ("simple", "moderate", "complex"):
                    complexity = value
                continue
            
            # Parse workers needed
            if line_upper.startswith("WORKERS_NEEDED:"):
                value = line_stripped.split(":", 1)[1].strip()
                workers_needed = self._parse_workers(value)
                continue
            
            # Track sections
            if line_upper.startswith("REASONING:"):
                current_section = "reasoning"
                continue
            if line_upper.startswith("PLAN:"):
                current_section = "plan"
                continue
            if line_upper.startswith("NOTES:"):
                current_section = "notes"
                continue
            
            # Collect content
            if current_section == "reasoning" and line_stripped:
                reasoning_lines.append(line_stripped)
            
            if current_section == "plan" and line_stripped:
                step = self._parse_step(line_stripped)
                if step:
                    steps.append(step)
        
        reasoning = " ".join(reasoning_lines)
        
        return ExecutionPlan(
            steps=steps,
            reasoning=reasoning,
            estimated_workers=workers_needed,
            complexity=complexity,
        )
    
    def _parse_workers(self, value: str) -> List[WorkerType]:
        """Parse the workers needed from a comma-separated string."""
        workers: List[WorkerType] = []
        
        worker_map = {
            "RETRIEVAL": WorkerType.RETRIEVAL,
            "WEB_SEARCH": WorkerType.WEB_SEARCH,
            "WEB": WorkerType.WEB_SEARCH,
            "SQL": WorkerType.SQL,
            "PLANNING": WorkerType.PLANNING,
        }
        
        for part in value.split(","):
            part_clean = part.strip().upper()
            if part_clean in worker_map:
                workers.append(worker_map[part_clean])
        
        return workers
    
    def _parse_step(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single step from the plan."""
        # Expected format: "1. Description -> WORKER: worker_type"
        
        # Remove leading number
        if line[0].isdigit():
            # Find the first space or period after the number
            for i, char in enumerate(line):
                if char in " .":
                    line = line[i+1:].strip()
                    break
        
        # Parse worker type
        worker_type = None
        description = line
        
        if "WORKER:" in line.upper():
            parts = line.upper().split("WORKER:")
            description = line[:line.upper().find("WORKER:")].strip(" ->")
            worker_str = parts[1].strip()
            
            worker_map = {
                "RETRIEVAL": WorkerType.RETRIEVAL,
                "WEB_SEARCH": WorkerType.WEB_SEARCH,
                "WEB": WorkerType.WEB_SEARCH,
                "SQL": WorkerType.SQL,
            }
            worker_type = worker_map.get(worker_str)
        
        if description:
            return {
                "description": description,
                "worker_type": worker_type.value if worker_type else None,
            }
        
        return None


def create_planning_worker(config=None) -> PlanningWorker:
    """Factory function to create a PlanningWorker."""
    return PlanningWorker(config=config)
