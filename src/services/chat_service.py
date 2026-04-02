"""Chat business logic extracted from the chat router.

Handles: input validation, thread resolution, XP awarding, cache invalidation,
SQL mode authorization, AgentConfig building, API key resolution, model params,
workspace context formatting, and message persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import UUID

from core.exceptions import AuthorizationError, ValidationError
from core.settings import AgentConfig
from infrastructure.cache.service import CacheService
from infrastructure.security.api_key_resolver import ApiKeyResolver
from models.message import MessageRole
from models.user import User, UserRole
from services.chat_history_service import ChatHistoryService
from services.settings_service import SettingsService
from services.xp_service import XPService
from utils.log import log_debug, log_error, log_info, log_warning


@dataclass
class ChatPrepResult:
    """Everything the streaming generator needs to produce a response."""

    thread_id: str
    user_id: UUID
    last_user_msg: str
    effective_question: str
    history: List[Dict[str, str]]
    config: AgentConfig
    user_api_key: Optional[str] = None
    user_model_params: Optional[Dict] = None
    user_api_keys: Optional[Dict[str, Optional[str]]] = None


class ChatService:
    """Encapsulates chat business logic that was previously in the router."""

    def __init__(
        self,
        chat_history: ChatHistoryService,
        xp_service: XPService,
        settings_service: SettingsService,
        cache: Optional[CacheService] = None,
    ) -> None:
        self._history = chat_history
        self._xp = xp_service
        self._settings = settings_service
        self._cache = cache

    def prepare_chat(
        self,
        user: User,
        messages: list,
        thread_id: Optional[str],
        mode: Optional[str],
        character: Optional[str],
        workspace_context=None,
        request_model_params: Optional[dict] = None,
    ) -> ChatPrepResult:
        """Validate input, resolve thread, award XP, build config.

        Returns a ChatPrepResult with all data needed by the streaming generator.
        """
        if not messages:
            raise ValidationError("messages array is empty")

        last_user_msg = None
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        if not last_user_msg:
            raise ValidationError("No user message found")

        user_id = user.id
        is_new_thread = thread_id is None
        resolved_thread_id = self._history.ensure_thread(
            user_id=user_id,
            thread_id=thread_id,
            title=last_user_msg[:60],
        )

        xp_amount = 2 + (5 if is_new_thread else 0)
        try:
            self._xp.award_xp(user_id, xp_amount, reason="chat_message")
        except Exception as e:
            log_warning(f"XP award failed (user={user_id}): {e}")

        if self._cache:
            try:
                uid_str = str(user_id)
                self._cache.invalidate_dashboard(uid_str)
                self._cache.invalidate_xp(uid_str)
                if is_new_thread:
                    self._cache.invalidate_threads(uid_str)
            except Exception as e:
                log_warning(f"Cache invalidation failed (user={user_id}): {e}")

        history = [
            {"role": m.role, "content": m.content}
            for m in messages[:-1]
        ]

        requested_mode = mode or "chat"
        if requested_mode == "sql" and user.role != UserRole.ADMIN:
            raise AuthorizationError("SQL mode is restricted to admin users only")

        config = AgentConfig(
            mode=requested_mode,
            character=character or "rio",
            user_role=user.role.value,
        )

        user_settings = None
        api_resolver = None
        try:
            user_settings = self._settings.get_or_create_settings(user.id)
            api_resolver = ApiKeyResolver(user_settings)
            if user_settings.model_name:
                config.model_name = user_settings.model_name
            config.enable_input_guardrail = user_settings.enable_input_guardrail
            config.enable_output_guardrail = user_settings.enable_output_guardrail
            config.enable_langsmith_tracing = user_settings.enable_langsmith_tracing
            config.langsmith_project = user_settings.langsmith_project
            log_debug(f"User settings loaded: model={user_settings.model_name}, temp={user_settings.temperature}")
        except Exception as e:
            log_error(f"Failed to load user settings: {e}")

        user_api_key = None
        all_user_api_keys = None
        if user_settings and api_resolver:
            model_name = config.model_name or user_settings.model_name
            if model_name:
                if "gpt" in model_name.lower() and "openrouter" not in model_name.lower():
                    user_api_key = api_resolver.get_openai_key()
                elif "openrouter" in model_name.lower() or "oss" in model_name.lower():
                    user_api_key = api_resolver.get_openrouter_key()

            all_user_api_keys = {
                "tavily": api_resolver.get_tavily_key(),
                "cohere": api_resolver.get_cohere_key(),
            }

            langsmith_key = api_resolver.get_langsmith_key()
            if langsmith_key is not None or not config.enable_langsmith_tracing:
                from infrastructure.telemetry.langsmith import apply_user_langsmith_settings
                apply_user_langsmith_settings(
                    api_key=langsmith_key,
                    tracing_enabled=config.enable_langsmith_tracing,
                    project=config.langsmith_project,
                )

        user_model_params = None
        if user_settings:
            user_model_params = {
                "temperature": user_settings.temperature,
                "max_tokens": user_settings.max_tokens,
                "top_p": user_settings.top_p,
                "frequency_penalty": user_settings.frequency_penalty,
                "presence_penalty": user_settings.presence_penalty,
            }
        # Per-request overrides take precedence over saved settings
        if request_model_params:
            if user_model_params is None:
                user_model_params = {}
            user_model_params.update(request_model_params)

        workspace_context_str = ""
        if workspace_context and workspace_context.chunks:
            ws = workspace_context
            parts = []
            if ws.file_trees:
                parts.append("## Workspace Files")
                for ft in ws.file_trees:
                    parts.append(f"- {ft.filePath}: {ft.tree}")
            parts.append("\n## Relevant Code Chunks")
            for chunk in ws.chunks:
                parts.append(f"\n### {chunk.filePath} :: {chunk.chunkName} ({chunk.chunkKind}) [L{chunk.startLine}-L{chunk.endLine}]")
                parts.append(f"```\n{chunk.content}\n```")
            workspace_context_str = "\n".join(parts)

        effective_question = last_user_msg
        if workspace_context_str:
            effective_question = f"[Workspace Context]\n{workspace_context_str}\n\n[User Question]\n{last_user_msg}"

        log_info(f"[REST] chat_stream: user={user.username} thread={resolved_thread_id} q={last_user_msg[:80]}")

        self._history.append_message_async(
            user_id=user_id,
            thread_id=resolved_thread_id,
            role=MessageRole.USER,
            content=last_user_msg,
        )

        return ChatPrepResult(
            thread_id=resolved_thread_id,
            user_id=user_id,
            last_user_msg=last_user_msg,
            effective_question=effective_question,
            history=history,
            config=config,
            user_api_key=user_api_key,
            user_model_params=user_model_params,
            user_api_keys=all_user_api_keys,
        )

    def persist_assistant_message(
        self,
        user_id: UUID,
        thread_id: str,
        content: str,
        run_id: Optional[str] = None,
        character_id: Optional[str] = None,
    ) -> None:
        """Persist the assistant's response after streaming completes."""
        if content:
            self._history.append_message_async(
                user_id=user_id,
                thread_id=thread_id,
                role=MessageRole.ASSISTANT,
                content=content,
                run_id=run_id,
                character_id=character_id,
            )
