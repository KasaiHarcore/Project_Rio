from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterable
from getpass import getpass

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from backend.utils.log import log_success, log_error, log_info
from backend.infrastructure.integrations.llm.form import MODEL_TEMP, Model, thread_cost, _init_thread_cost


class OpenRouterModel(Model):
    def __init__(
        self,
        name: str,
        model_name: str,
        cost_per_input: float,
        cost_per_output: float,
        parallel_tool_call: bool = True,
    ):
        super().__init__(
            name=name,
            cost_per_input=cost_per_input,
            cost_per_output=cost_per_output,
            parallel_tool_call=parallel_tool_call,
        )
        self.model_name = model_name
        self.llm: ChatOpenAI | None = None

    def check_api_key(self) -> str:
        """Ensure OPENROUTER_API_KEY is available."""
        env_key = os.getenv("OPENROUTER_API_KEY")
        if env_key:
            log_success("OpenRouter API key detected")
            return env_key

        log_error("OPENROUTER_API_KEY is not set")
        if not sys.stdin.isatty():
            raise RuntimeError(
                "OPENROUTER_API_KEY missing and no interactive prompt available. Set the env var before running."
            )

        try:
            api_key = getpass("Enter OpenRouter API Key: ").strip()
        except KeyboardInterrupt:
            log_error("API key input cancelled by user")
            raise RuntimeError("Missing OpenRouter API key")

        if not api_key:
            raise RuntimeError("API key cannot be empty")

        os.environ["OPENROUTER_API_KEY"] = api_key
        log_success("OpenRouter API key provided manually")
        return api_key

    def setup(self) -> None:
        log_info(f"Setting up OpenRouter model: {self.model_name}")
        self.check_api_key()

        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=MODEL_TEMP,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            request_timeout=60.0,
            max_retries=2,
        )

        log_success(f"OpenRouter model ready: {self.model_name}")

    def call(
        self,
        *,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        ai_prompt: str | None = None,
        messages: list[BaseMessage] | None = None,
        **kwargs,
    ):
        if not self.llm:
            log_info("LLM not initialized, setting up...")
            self.setup()

        response_prefix: str = kwargs.pop("response_prefix", "")
        response_suffix: str = kwargs.pop("response_suffix", "")
        response_transform: Callable[[str], str] | None = kwargs.pop("response_transform", None)
        return_text: bool = bool(kwargs.pop("return_text", False))

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

        response = self.llm.invoke(lc_messages, **kwargs)
        log_success(f"Received response from {self.model_name}")

        usage = response.response_metadata.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = self.calc_cost(input_tokens, output_tokens)

        _init_thread_cost()
        thread_cost.process_input_tokens += input_tokens
        thread_cost.process_output_tokens += output_tokens
        thread_cost.process_cost += cost

        text = getattr(response, "content", "")
        if response_prefix or response_suffix:
            text = f"{response_prefix}{text}{response_suffix}"
        if response_transform:
            text = response_transform(text)

        if return_text:
            return text
        try:
            response.ui_text = text  # type: ignore[attr-defined]
        except Exception:
            pass
        return response

    def stream(
        self,
        *,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        ai_prompt: str | None = None,
        messages: list[BaseMessage] | None = None,
        **kwargs,
    ) -> Iterable[str]:
        """Stream tokens from the OpenRouter model."""
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


class OpenAI_OSS_120B_Free(OpenRouterModel):
    def __init__(self):
        super().__init__(
            name="gpt-oss-120b_free",
            model_name="openai/gpt-oss-120b:free",
            cost_per_input=0.0,
            cost_per_output=0.0,
            parallel_tool_call=True,
        )
        self.note = "OpenRouter OSS 120B (free)"
        
class OpenAI_OSS_120B_Paid(OpenRouterModel):
    def __init__(self):
        super().__init__(
            name="gpt-oss-120b_paid",
            model_name="openai/gpt-oss-120b",
            cost_per_input=0.000000039,
            cost_per_output=0.0000019,
            parallel_tool_call=True,
        )
        self.note = "OpenRouter OSS 120B (paid)"
