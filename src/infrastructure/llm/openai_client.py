from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from getpass import getpass

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from utils.log import log_success, log_error, log_info
from infrastructure.llm.form import MODEL_TEMP, Model


class OpenAIModel(Model):
    def __init__(
        self,
        name: str,
        model_name: str,
        cost_per_input: float,
        cost_per_output: float,
    ):
        super().__init__(
            name=name,
            cost_per_input=cost_per_input,
            cost_per_output=cost_per_output,
        )
        self.model_name = model_name
        self.llm: ChatOpenAI | None = None
        # User configuration (set via set_user_config)
        self._user_api_key: str | None = None
        self._user_temperature: float | None = None
        self._user_max_tokens: int | None = None
        self._user_top_p: float | None = None
        self._user_frequency_penalty: float | None = None
        self._user_presence_penalty: float | None = None

    def set_user_config(
        self,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
    ) -> None:
        """Set user-specific configuration for this model instance."""
        self._user_api_key = api_key
        self._user_temperature = temperature
        self._user_max_tokens = max_tokens
        self._user_top_p = top_p
        self._user_frequency_penalty = frequency_penalty
        self._user_presence_penalty = presence_penalty
        # Invalidate existing client so setup() re-creates it with new config
        self.llm = None
        log_info(f"User configuration set for {self.model_name}")

    def check_api_key(self) -> str:
        """Ensure OPENAI_API_KEY is available (user key > env var > manual input)."""
        if self._user_api_key:
            log_success("Using user's OpenAI API key")
            return self._user_api_key

        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            log_success("OpenAI API key detected from environment")
            return env_key

        log_error("OPENAI_API_KEY is not set")
        if not sys.stdin.isatty():
            raise RuntimeError(
                "OPENAI_API_KEY missing and no interactive prompt available. "
                "Set the env var before running."
            )

        try:
            api_key = getpass("Enter OpenAI API Key: ").strip()
        except KeyboardInterrupt:
            log_error("API key input cancelled by user")
            raise RuntimeError("Missing OpenAI API key")

        if not api_key:
            raise RuntimeError("API key cannot be empty")

        log_success("OpenAI API key provided manually")
        return api_key

    def setup(self) -> None:
        log_info(f"Setting up OpenAI model: {self.model_name}")
        api_key = self.check_api_key()

        temperature = (
            self._user_temperature
            if self._user_temperature is not None
            else MODEL_TEMP
        )

        llm_kwargs: dict = {
            "model": self.model_name,
            "temperature": temperature,
            "api_key": api_key,
            "timeout": 60.0,
            "max_retries": 2,
        }

        if self._user_max_tokens is not None:
            llm_kwargs["max_tokens"] = self._user_max_tokens
        if self._user_top_p is not None:
            llm_kwargs["top_p"] = self._user_top_p
        if self._user_frequency_penalty is not None:
            llm_kwargs["frequency_penalty"] = self._user_frequency_penalty
        if self._user_presence_penalty is not None:
            llm_kwargs["presence_penalty"] = self._user_presence_penalty

        self.llm = ChatOpenAI(**llm_kwargs)
        log_success(f"OpenAI model ready: {self.model_name} (temp={temperature})")

    def stream(
        self,
        *,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        ai_prompt: str | None = None,
        messages: list[BaseMessage] | None = None,
        **kwargs,
    ) -> Iterable[str]:
        """Stream tokens from the OpenAI model."""
        if not self.llm:
            log_info("LLM not initialized, setting up...")
            self.setup()

        if messages is not None:
            lc_messages = messages
        else:
            if user_prompt is None:
                raise ValueError("Either `messages` or `user_prompt` must be provided")
            lc_messages = self.format_messages(
                system_prompt=system_prompt or "",
                ai_prompt=ai_prompt,
                user_prompt=user_prompt,
            )

        for chunk in self.llm.stream(lc_messages, **kwargs):
            text = getattr(chunk, "content", "")
            if text:
                yield text


# ---------------------------------------------------------------------------
# Concrete model variants
# ---------------------------------------------------------------------------

class OpenAI_GPT52(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5.2",
            model_name="gpt-5.2-2025-12-11",
            cost_per_input=0.00000175,
            cost_per_output=0.000014,
        )


class OpenAI_GPT5_mini(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5-mini",
            model_name="gpt-5-mini-2025-08-07",
            cost_per_input=0.00000025,
            cost_per_output=0.000002,
        )


class OpenAI_GPT5_nano(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5-nano",
            model_name="gpt-5-nano-2025-08-07",
            cost_per_input=0.00000005,
            cost_per_output=0.000004,
        )


class OpenAI_GPT5_pro(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5-pro",
            model_name="gpt-5.2-pro-2025-12-11",
            cost_per_input=0.000015,
            cost_per_output=0.00012,
        )


class OpenAI_GPT5(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5",
            model_name="gpt-5-2025-08-07",
            cost_per_input=0.00000125,
            cost_per_output=0.00001,
        )


class OpenAI_GPT41(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-4.1",
            model_name="gpt-4.1-2025-04-14",
            cost_per_input=0.000002,
            cost_per_output=0.000008,
        )
