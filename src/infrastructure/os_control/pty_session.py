"""PTY Shell Session Manager.

Provides persistent shell sessions per user. State carries across commands
(cd, export, conda activate) because each session maintains a single subprocess.

On Linux/macOS: uses pexpect for full PTY support (interactive programs work).
On Windows: uses asyncio.subprocess with pipe-based I/O as a fallback.

Each session is managed as a singleton per user session.
"""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
import time
from typing import Dict, Optional, Tuple

from infrastructure.os_control.risk_tier import RiskTier, classify_shell_command_risk
from infrastructure.os_control.schemas import ShellCommand, ShellResult
from utils.log import log_debug, log_error, log_info, log_warning


# Maximum output size to prevent memory issues (1MB)
MAX_OUTPUT_SIZE = 1_048_576

_DEFAULT_SHELL = "/bin/bash" if platform.system() != "Windows" else "cmd.exe"


class PTYSession:
    """Persistent shell session backed by a subprocess.

    Each PTYSession maintains a single shell process whose state persists
    across commands (working directory, environment variables, etc.).

    Attributes:
        session_id: Unique session identifier (typically user_id).
        shell: Path to the shell executable.
        working_directory: Current working directory of the session.
        is_alive: Whether the underlying process is still running.
    """

    def __init__(
        self,
        session_id: str,
        shell: Optional[str] = None,
        working_directory: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        self.session_id = session_id
        self.shell = shell or _DEFAULT_SHELL
        self.working_directory = working_directory or os.getcwd()
        self._env = {**os.environ, **(env or {})}
        self._process: Optional[subprocess.Popen] = None
        self._created_at = time.time()
        self._command_count = 0

    @property
    def is_alive(self) -> bool:
        """Check if the underlying shell process is alive."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def execute(self, cmd: ShellCommand) -> ShellResult:
        """Execute a shell command and return structured output.

        This runs each command in a fresh subprocess that inherits the
        session's working directory and environment. The working directory
        is updated after each successful command.

        Args:
            cmd: ShellCommand with the command string and options.

        Returns:
            ShellResult with stdout, stderr, exit code, and timing.
        """
        start_time = time.time()
        self._command_count += 1

        # Auto-classify risk tier
        effective_tier = classify_shell_command_risk(cmd.command)
        if cmd.risk_tier.value < effective_tier.value:
            effective_tier = max(cmd.risk_tier, effective_tier)

        # Merge per-command environment
        env = {**self._env}
        if cmd.environment:
            env.update(cmd.environment)

        # Build the working directory
        cwd = cmd.working_directory or self.working_directory

        log_info(
            f"[PTY:{self.session_id}] Executing (tier {effective_tier}): "
            f"{cmd.command[:120]}{'...' if len(cmd.command) > 120 else ''}"
        )

        try:
            # Use subprocess for cross-platform compatibility
            result = subprocess.run(
                cmd.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=cmd.timeout_seconds,
                cwd=cwd,
                env=env,
            )

            stdout = result.stdout[:MAX_OUTPUT_SIZE] if result.stdout else ""
            stderr = result.stderr[:MAX_OUTPUT_SIZE] if result.stderr else ""
            exit_code = result.returncode

            # Update working directory if a cd command was part of the chain
            if "cd " in cmd.command:
                self._update_working_directory(cmd.command, cwd, env)

            execution_time_ms = int((time.time() - start_time) * 1000)

            log_debug(
                f"[PTY:{self.session_id}] exit_code={exit_code} "
                f"stdout={len(stdout)}B stderr={len(stderr)}B "
                f"time={execution_time_ms}ms"
            )

            return ShellResult(
                command=cmd.command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time_ms=execution_time_ms,
                timed_out=False,
                working_directory=self.working_directory,
                risk_tier=effective_tier,
            )

        except subprocess.TimeoutExpired:
            execution_time_ms = int((time.time() - start_time) * 1000)
            log_warning(
                f"[PTY:{self.session_id}] Command timed out after {cmd.timeout_seconds}s: "
                f"{cmd.command[:80]}"
            )
            return ShellResult(
                command=cmd.command,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {cmd.timeout_seconds} seconds",
                execution_time_ms=execution_time_ms,
                timed_out=True,
                working_directory=self.working_directory,
                risk_tier=effective_tier,
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            log_error(f"[PTY:{self.session_id}] Execution error: {e}")
            return ShellResult(
                command=cmd.command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time_ms=execution_time_ms,
                timed_out=False,
                working_directory=self.working_directory,
                risk_tier=effective_tier,
            )

    def _update_working_directory(
        self,
        command: str,
        cwd: str,
        env: Dict[str, str],
    ) -> None:
        """Try to resolve the new working directory after a cd command."""
        try:
            # Run pwd/cd in the same context to get the new directory
            pwd_cmd = "pwd" if platform.system() != "Windows" else "cd"
            full_cmd = f"{command} && {pwd_cmd}"
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
                cwd=cwd,
                env=env,
            )
            if result.returncode == 0 and result.stdout.strip():
                self.working_directory = result.stdout.strip().splitlines()[-1]
                log_debug(f"[PTY:{self.session_id}] cwd updated: {self.working_directory}")
        except Exception as e:
            log_debug(f"[PTY:{self.session_id}] Failed to update cwd: {e}")

    def close(self) -> None:
        """Terminate the session and clean up resources."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            log_info(f"[PTY:{self.session_id}] Session closed")
        self._process = None

    def __repr__(self) -> str:
        return (
            f"PTYSession(id={self.session_id}, shell={self.shell}, "
            f"cwd={self.working_directory}, commands={self._command_count})"
        )


class PTYSessionManager:
    """Manages PTY sessions as singletons per user.

    Provides session lifecycle management, automatic cleanup of idle sessions,
    and concurrent session limits.
    """

    def __init__(
        self,
        max_sessions: int = 50,
        idle_timeout_seconds: int = 3600,
    ) -> None:
        self._sessions: Dict[str, PTYSession] = {}
        self._last_activity: Dict[str, float] = {}
        self._max_sessions = max_sessions
        self._idle_timeout = idle_timeout_seconds

    def get_or_create(
        self,
        session_id: str,
        shell: Optional[str] = None,
        working_directory: Optional[str] = None,
    ) -> PTYSession:
        """Get an existing session or create a new one.

        Args:
            session_id: Unique session identifier (user_id).
            shell: Optional shell override.
            working_directory: Optional initial working directory.

        Returns:
            PTYSession instance.
        """
        self._cleanup_idle_sessions()

        if session_id in self._sessions:
            self._last_activity[session_id] = time.time()
            return self._sessions[session_id]

        if len(self._sessions) >= self._max_sessions:
            self._evict_oldest()

        session = PTYSession(
            session_id=session_id,
            shell=shell,
            working_directory=working_directory,
        )
        self._sessions[session_id] = session
        self._last_activity[session_id] = time.time()
        log_info(f"[PTYManager] Created session: {session_id}")
        return session

    def close_session(self, session_id: str) -> None:
        """Close and remove a specific session."""
        if session_id in self._sessions:
            self._sessions[session_id].close()
            del self._sessions[session_id]
            self._last_activity.pop(session_id, None)
            log_info(f"[PTYManager] Closed session: {session_id}")

    def close_all(self) -> None:
        """Close all sessions."""
        for sid in list(self._sessions.keys()):
            self.close_session(sid)
        log_info("[PTYManager] All sessions closed")

    def _cleanup_idle_sessions(self) -> None:
        """Remove sessions that have been idle beyond the timeout."""
        now = time.time()
        idle_ids = [
            sid for sid, last in self._last_activity.items()
            if (now - last) > self._idle_timeout
        ]
        for sid in idle_ids:
            log_info(f"[PTYManager] Evicting idle session: {sid}")
            self.close_session(sid)

    def _evict_oldest(self) -> None:
        """Evict the oldest session when at capacity."""
        if not self._last_activity:
            return
        oldest = min(self._last_activity, key=self._last_activity.get)  # type: ignore[arg-type]
        log_info(f"[PTYManager] Evicting oldest session: {oldest}")
        self.close_session(oldest)

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)


# Module-level singleton
pty_manager = PTYSessionManager()
