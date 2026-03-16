"""OS Control Worker — executes operating system commands via the LangGraph workflow.

The OS Control Worker is a specialized agent that:
- Receives OS-related tasks from the supervisor
- Classifies the risk tier of requested actions
- Executes shell commands, browser actions, or GUI actions
- Uses LLM to plan multi-step OS operations
- Streams stdout/stderr back as real-time context
- Triggers approval gates for tier 3+ operations

This worker calls OS tools through the service layer — it reasons, loops,
and multi-steps. It is NOT an MCP tool (those are deterministic single-purpose).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from workflows.state import AgentState, WorkerResult, WorkerType
from workflows.workers.base import BaseWorker
from infrastructure.os_control.risk_tier import RiskTier, classify_shell_command_risk
from infrastructure.os_control.schemas import OSActionType
from utils.log import log_debug, log_error, log_info, log_warning


OS_CONTROL_SYSTEM_PROMPT = """I am the OS Control module — a specialized component that executes operating system commands on behalf of Sensei.

## My Capabilities
- Execute shell commands (bash/cmd) with persistent session state
- Navigate and interact with web pages via browser automation
- Control desktop GUI elements programmatically
- Chain multiple commands together for complex operations

## Safety Rules
- I ALWAYS classify commands by risk tier before execution
- Tier 1 (none): read-only commands like ls, cat, pwd, git status
- Tier 2 (soft): low-risk writes like creating directories
- Tier 3 (hard): file mutations, git operations, docker commands
- Tier 4 (explicit): sudo, package management, kill, system services
- Tier 5 (destructive): rm -rf, format, dd — requires typed confirmation
- I NEVER execute destructive commands without explicit approval
- I explain what each command does before executing it
- I report results clearly with exit codes and relevant output

## Output Format
For each command I execute, I provide:
1. The command being run
2. Its risk classification
3. The output (stdout/stderr)
4. Exit code and success/failure status
5. Any relevant observations about the result

I refer to the user as Sensei.
"""


class OSControlWorker(BaseWorker):
    """LangGraph worker for operating system command execution.

    Routes OS tasks through the PTY session manager and formats
    results for the supervisor's synthesis step.
    """

    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.OS_CONTROL

    @property
    def name(self) -> str:
        return "OS Control Worker"

    @property
    def description(self) -> str:
        return "Executes shell commands, browser actions, and GUI operations on the OS"

    @property
    def system_prompt(self) -> str:
        return OS_CONTROL_SYSTEM_PROMPT

    def _execute(self, state: AgentState) -> WorkerResult:
        """Execute OS control operations based on the user's request.

        The worker uses the LLM to:
        1. Parse the user's intent into concrete OS actions
        2. Classify risk tiers for each action
        3. Execute approved actions via the service layer
        4. Compile results into a structured response

        Args:
            state: Current agent state.

        Returns:
            WorkerResult with command outputs and metadata.
        """
        question = self.get_question(state)
        reasoning = self.get_last_decision_reasoning(state)
        user_id = state.get("user_id") or "anonymous"

        # Use LLM to plan the OS operations
        plan = self._plan_operations(question, reasoning)

        if not plan:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="Could not determine what OS operations to perform.",
                error="Failed to plan OS operations",
            )

        # Execute the planned operations
        results = []
        all_success = True

        for step in plan:
            step_type = step.get("type", "shell")
            command = step.get("command", "")
            description = step.get("description", "")

            if not command:
                continue

            if step_type == "shell":
                result = self._execute_shell(command, user_id, description)
                results.append(result)
                if not result.get("success"):
                    all_success = False
                    # Stop on failure unless the plan says to continue
                    if not step.get("continue_on_error", False):
                        break

        # Format all results
        formatted = self._format_results(results, plan)

        return WorkerResult(
            worker_type=self.worker_type,
            success=all_success,
            content=formatted,
            metadata={
                "commands_executed": len(results),
                "all_success": all_success,
                "risk_tiers": [r.get("risk_tier", 4) for r in results],
            },
        )

    def _plan_operations(
        self,
        question: str,
        reasoning: str,
    ) -> List[Dict[str, Any]]:
        """Use LLM to plan OS operations from the user's request.

        Returns a list of operation steps, each with:
        - type: "shell", "browser", or "gui"
        - command: The actual command/action
        - description: Human-readable explanation
        - continue_on_error: Whether to proceed if this step fails
        """
        prompt = f"""Given Sensei's request, plan the OS operations needed.

Sensei's request: {question}
{f"Additional context: {reasoning}" if reasoning else ""}

Return a JSON array of operation steps. Each step has:
- "type": "shell" (for terminal commands)
- "command": the exact command to run
- "description": brief explanation of what this does
- "continue_on_error": true/false

IMPORTANT:
- Use the simplest commands possible
- Prefer read-only operations when the intent is informational
- Chain related commands logically
- Never use interactive commands (vim, nano, ssh without -t, etc.)

Example output:
[
  {{"type": "shell", "command": "pwd", "description": "Check current directory", "continue_on_error": true}},
  {{"type": "shell", "command": "ls -la", "description": "List all files", "continue_on_error": false}}
]

Return ONLY the JSON array, no markdown or explanation."""

        try:
            response = self._call_llm(user_prompt=prompt)
            # Parse JSON from response
            content = response.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                content = re.sub(r"```(?:json)?\s*", "", content)
                content = content.replace("```", "").strip()

            # Find JSON array
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                plan = json.loads(match.group())
                if isinstance(plan, list):
                    return plan

            log_warning(f"[OSControl] Failed to parse plan from LLM: {content[:200]}")
            return []

        except Exception as e:
            log_error(f"[OSControl] Planning failed: {e}")
            # Fallback: treat the entire question as a single command
            # Only if it looks like a command
            if any(
                question.strip().startswith(p)
                for p in ("ls", "cd", "pwd", "cat", "echo", "git", "python", "node", "npm")
            ):
                return [{
                    "type": "shell",
                    "command": question.strip(),
                    "description": "Direct command execution",
                    "continue_on_error": False,
                }]
            return []

    def _execute_shell(
        self,
        command: str,
        user_id: str,
        description: str,
    ) -> Dict[str, Any]:
        """Execute a single shell command via the OS control service.

        Args:
            command: Shell command to run.
            user_id: User ID for session management.
            description: Human-readable description.

        Returns:
            Dict with execution results.
        """
        from services.os_control_service import os_control_service

        risk_tier = classify_shell_command_risk(command)

        log_info(
            f"[OSControlWorker] Executing: {command[:80]} "
            f"(tier={risk_tier}, user={user_id})"
        )

        result = os_control_service.execute_shell(
            command=command,
            user_id=user_id,
        )

        return {
            "command": result.command,
            "description": description,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.success,
            "timed_out": result.timed_out,
            "risk_tier": result.risk_tier.value,
            "execution_time_ms": result.execution_time_ms,
        }

    def _format_results(
        self,
        results: List[Dict[str, Any]],
        plan: List[Dict[str, Any]],
    ) -> str:
        """Format execution results for the supervisor.

        Args:
            results: List of execution result dicts.
            plan: Original execution plan.

        Returns:
            Formatted markdown string.
        """
        if not results:
            return "No commands were executed."

        parts = ["## OS Command Execution Results\n"]

        for i, result in enumerate(results, 1):
            status = "OK" if result["success"] else "FAILED"
            tier_label = f"Tier {result['risk_tier']}"

            parts.append(f"\n### Step {i}: {result['description']}")
            parts.append(f"**Command:** `{result['command']}`")
            parts.append(f"**Status:** {status} (exit code: {result['exit_code']}) | {tier_label}")
            parts.append(f"**Time:** {result['execution_time_ms']}ms")

            if result["stdout"]:
                # Truncate very long output
                stdout = result["stdout"]
                if len(stdout) > 2000:
                    stdout = stdout[:2000] + "\n... (output truncated)"
                parts.append(f"\n**Output:**\n```\n{stdout}\n```")

            if result["stderr"]:
                stderr = result["stderr"]
                if len(stderr) > 1000:
                    stderr = stderr[:1000] + "\n... (truncated)"
                parts.append(f"\n**Errors:**\n```\n{stderr}\n```")

            if result["timed_out"]:
                parts.append("\n**Warning:** Command timed out.")

        return "\n".join(parts)
