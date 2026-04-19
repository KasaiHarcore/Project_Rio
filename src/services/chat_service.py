"""Chat business logic extracted from the chat router.

Handles: input validation, thread resolution, XP awarding, cache invalidation,
SQL mode authorization, AgentConfig building, API key resolution, model params,
workspace context formatting, and message persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import UUID, uuid4

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
    user_message_id: Optional[str] = None


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
            config.enable_phoenix_tracing = user_settings.enable_phoenix_tracing
            config.phoenix_project = user_settings.phoenix_project
            log_debug(f"User settings loaded: model={user_settings.model_name}, temp={user_settings.temperature}")
        except Exception as e:
            log_error(f"Failed to load user settings: {e}")

        user_api_key = None
        all_user_api_keys = None
        if user_settings and api_resolver:
            from infrastructure.llm import form
            from infrastructure.llm.openrouter_client import OpenRouterModel

            # Resolve the model so we can check its actual type
            model_name = config.model_name or user_settings.model_name
            if model_name:
                try:
                    form.set_model(model_name)
                except ValueError:
                    pass

            if isinstance(form.SELECTED_MODEL, OpenRouterModel):
                user_api_key = api_resolver.get_openrouter_key()
            elif form.SELECTED_MODEL is not None:
                user_api_key = api_resolver.get_openai_key()

            all_user_api_keys = {
                "tavily": api_resolver.get_tavily_key(),
                "cohere": api_resolver.get_cohere_key(),
            }

            # Apply Phoenix tracing settings (self-hosted, no per-user API key)
            from infrastructure.telemetry.phoenix import apply_user_phoenix_settings
            apply_user_phoenix_settings(
                tracing_enabled=config.enable_phoenix_tracing,
                project=config.phoenix_project,
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

        # Generate a stable UUID for the user message so the assistant
        # message can reference it as parent_id (conversation chaining).
        user_msg_id = str(uuid4())

        # Find the latest message in the thread to use as parent for the
        # new user message (chains user→assistant→user→assistant…).
        parent_for_user = self._history.get_latest_message_id(resolved_thread_id)

        self._history.append_message_async(
            user_id=user_id,
            thread_id=resolved_thread_id,
            role=MessageRole.USER,
            content=last_user_msg,
            message_id=user_msg_id,
            parent_id=parent_for_user,
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
            user_message_id=user_msg_id,
        )

    def prepare_regeneration(
        self,
        user: User,
        thread_id: str,
        message_id: str,
        character: Optional[str] = None,
    ) -> ChatPrepResult:
        """Build a ChatPrepResult for regenerating a response to a specific user message.

        Fetches all messages in the thread up to and including the target user
        message, then constructs the same prep structure as prepare_chat.
        """
        from uuid import UUID as _UUID

        user_id = user.id
        thread_uuid = _UUID(thread_id)
        message_uuid = _UUID(message_id)

        # Verify thread ownership
        thread = self._history.get_thread_if_owned(thread_uuid, user_id)
        if not thread:
            raise ValidationError("Thread not found or not owned by user")

        # Fetch all messages and find the target
        all_messages = self._history.get_messages(thread_id=thread_uuid, limit=500)
        target_msg = None
        history_messages = []
        for msg in all_messages:
            if msg.id == message_uuid:
                target_msg = msg
                break
            history_messages.append(msg)

        if not target_msg or target_msg.role.value != "user":
            raise ValidationError("Target message not found or is not a user message")

        history = [
            {"role": m.role.value, "content": m.content}
            for m in history_messages
        ]

        config = AgentConfig(
            mode="chat",
            character=character or "rio",
            user_role=user.role.value,
        )

        # Load user settings for model config
        user_model_params = None
        user_api_key = None
        all_user_api_keys = None
        try:
            user_settings = self._settings.get_or_create_settings(user.id)
            if user_settings.model_name:
                config.model_name = user_settings.model_name
            config.enable_input_guardrail = user_settings.enable_input_guardrail
            config.enable_output_guardrail = user_settings.enable_output_guardrail

            api_resolver = ApiKeyResolver(user_settings)
            from infrastructure.llm import form
            from infrastructure.llm.openrouter_client import OpenRouterModel

            model_name = config.model_name or user_settings.model_name
            if model_name:
                try:
                    form.set_model(model_name)
                except ValueError:
                    pass

            if isinstance(form.SELECTED_MODEL, OpenRouterModel):
                user_api_key = api_resolver.get_openrouter_key()
            elif form.SELECTED_MODEL is not None:
                user_api_key = api_resolver.get_openai_key()

            all_user_api_keys = {
                "tavily": api_resolver.get_tavily_key(),
                "cohere": api_resolver.get_cohere_key(),
            }

            user_model_params = {
                "temperature": user_settings.temperature,
                "max_tokens": user_settings.max_tokens,
                "top_p": user_settings.top_p,
                "frequency_penalty": user_settings.frequency_penalty,
                "presence_penalty": user_settings.presence_penalty,
            }
        except Exception as e:
            log_error(f"Failed to load user settings for regeneration: {e}")

        return ChatPrepResult(
            thread_id=thread_id,
            user_id=user_id,
            last_user_msg=target_msg.content,
            effective_question=target_msg.content,
            history=history,
            config=config,
            user_api_key=user_api_key,
            user_model_params=user_model_params,
            user_api_keys=all_user_api_keys,
        )

    def prepare_edit(
        self,
        user: User,
        thread_id: str,
        message_id: str,
        new_content: str,
        character: Optional[str] = None,
    ) -> ChatPrepResult:
        """Build a ChatPrepResult for editing a previously-sent user message.

        The edit creates a NEW user message as a sibling of the original
        (shares ``parent_id``). History sent to the agent ends right before
        the original target — the new edited message replaces it on the
        new branch. The caller persists the assistant response as a child
        of the new user message.
        """
        user_id = user.id
        thread_uuid = UUID(thread_id)
        message_uuid = UUID(message_id)

        thread = self._history.get_thread_if_owned(thread_uuid, user_id)
        if not thread:
            raise ValidationError("Thread not found or not owned by user")

        cleaned = (new_content or "").strip()
        if not cleaned:
            raise ValidationError("new_content cannot be empty")

        all_messages = self._history.get_messages(thread_id=thread_uuid, limit=500)
        target_msg = None
        history_messages: list = []
        for msg in all_messages:
            if msg.id == message_uuid:
                target_msg = msg
                break
            history_messages.append(msg)

        if not target_msg or target_msg.role.value != "user":
            raise ValidationError("Target message not found or is not a user message")

        # History = everything strictly before the original user message.
        history = [
            {"role": m.role.value, "content": m.content}
            for m in history_messages
        ]

        config = AgentConfig(
            mode="chat",
            character=character or "rio",
            user_role=user.role.value,
        )

        # Load user settings (mirrors prepare_regeneration) so edits pick
        # up the same model + guardrail + API-key configuration.
        user_model_params = None
        user_api_key = None
        all_user_api_keys = None
        try:
            user_settings = self._settings.get_or_create_settings(user.id)
            if user_settings.model_name:
                config.model_name = user_settings.model_name
            config.enable_input_guardrail = user_settings.enable_input_guardrail
            config.enable_output_guardrail = user_settings.enable_output_guardrail

            api_resolver = ApiKeyResolver(user_settings)
            from infrastructure.llm import form
            from infrastructure.llm.openrouter_client import OpenRouterModel

            model_name = config.model_name or user_settings.model_name
            if model_name:
                try:
                    form.set_model(model_name)
                except ValueError:
                    pass

            if isinstance(form.SELECTED_MODEL, OpenRouterModel):
                user_api_key = api_resolver.get_openrouter_key()
            elif form.SELECTED_MODEL is not None:
                user_api_key = api_resolver.get_openai_key()

            all_user_api_keys = {
                "tavily": api_resolver.get_tavily_key(),
                "cohere": api_resolver.get_cohere_key(),
            }

            user_model_params = {
                "temperature": user_settings.temperature,
                "max_tokens": user_settings.max_tokens,
                "top_p": user_settings.top_p,
                "frequency_penalty": user_settings.frequency_penalty,
                "presence_penalty": user_settings.presence_penalty,
            }
        except Exception as e:
            log_error(f"Failed to load user settings for edit: {e}")

        # Persist the NEW sibling user message (parent_id = original's parent)
        new_user_msg_id = str(uuid4())
        sibling_parent_id = str(target_msg.parent_id) if target_msg.parent_id else None

        self._history.append_message_async(
            user_id=user_id,
            thread_id=thread_id,
            role=MessageRole.USER,
            content=cleaned,
            message_id=new_user_msg_id,
            parent_id=sibling_parent_id,
        )

        log_info(
            f"[REST] chat edit: user={user.username} thread={thread_id} "
            f"edited_msg={message_id[:8]} new_msg={new_user_msg_id[:8]} q={cleaned[:80]}"
        )

        return ChatPrepResult(
            thread_id=thread_id,
            user_id=user_id,
            last_user_msg=cleaned,
            effective_question=cleaned,
            history=history,
            config=config,
            user_api_key=user_api_key,
            user_model_params=user_model_params,
            user_api_keys=all_user_api_keys,
            user_message_id=new_user_msg_id,
        )

    def persist_assistant_message(
        self,
        user_id: UUID,
        thread_id: str,
        content: str,
        run_id: Optional[str] = None,
        character_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        user_message_id: Optional[str] = None,
        message_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Persist the assistant's response after streaming completes.

        ``parent_id`` from the request body takes precedence (explicit
        branching).  Falls back to ``user_message_id`` so every assistant
        message chains to the user message that triggered it.

        ``message_id`` lets the caller pre-allocate the UUID so it can be
        echoed in the streaming ``message-persisted`` SSE event before the
        async write finishes.
        """
        if content:
            effective_parent = parent_id or user_message_id
            self._history.append_message_async(
                user_id=user_id,
                thread_id=thread_id,
                role=MessageRole.ASSISTANT,
                content=content,
                run_id=run_id,
                character_id=character_id,
                parent_id=effective_parent,
                message_id=message_id,
                metadata=metadata,
            )
