from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from getpass import getpass
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from backend.utils.log import log_success, log_error, log_info
from backend.api.form import MODEL_TEMP, Model, thread_cost, _init_thread_cost

class OpenAIModel(Model):
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
        """
        Ensure OPENAI_API_KEY is available.
        """
        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            log_success("OpenAI API key detected")
            return env_key

        log_error("OPENAI_API_KEY is not set")

        while True:
            try:
                api_key = getpass("Enter OpenAI API Key: ").strip()
            except KeyboardInterrupt:
                log_error("API key input cancelled by user")
                raise RuntimeError("Missing OpenAI API key")

            if not api_key:
                log_error("API key cannot be empty")
                continue

            # Set for current process
            os.environ["OPENAI_API_KEY"] = api_key

            log_success("OpenAI API key provided manually")
            return api_key
    
    def setup(self) -> None:
        log_info(f"Setting up OpenAI model: {self.model_name}")

        self.check_api_key()

        # Add timeout to prevent hanging (60 seconds default)
        self.llm = ChatOpenAI(
            model=self.model_name, 
            temperature=MODEL_TEMP,
            request_timeout=60.0,
            max_retries=2
        )

        log_success(f"OpenAI model ready: {self.model_name}")
        
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
        response_transform: Callable[[str], str] | None = kwargs.pop(
            "response_transform", None
        )
        return_text: bool = bool(kwargs.pop("return_text", False))

        if messages is not None:
            lc_messages = messages
        else:
            if user_prompt is None:
                raise ValueError("Either `messages` or `user_prompt` must be provided")

            lc_messages = self.format_messages(
                system_prompt=system_prompt,
                ai_prompt=ai_prompt,
                user_prompt=user_prompt
            )

        # Invoke LLM
        response = self.llm.invoke(lc_messages, **kwargs)
        log_success(f"Received response from {self.model_name}")

        # Token usage & cost
        usage = response.response_metadata.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        cost = self.calc_cost(input_tokens, output_tokens)

        _init_thread_cost()
        thread_cost.process_input_tokens += input_tokens
        thread_cost.process_output_tokens += output_tokens
        thread_cost.process_cost += cost

        # Extract & post-process text
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

class OpenAI_GPT52(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5.2",
            model_name="gpt-5.2-2025-12-11",
            cost_per_input=0.0,
            cost_per_output=0.0,
            parallel_tool_call=True,
        )
        self.note = "OpenAI's GPT-5.2 model released on 11th December 2025"
        
class OpenAI_GPT5_mini(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5-mini",
            model_name="gpt-5-mini-2025-08-07",
            cost_per_input=0.0,
            cost_per_output=0.0,
            parallel_tool_call=True,
        )
        self.note = "OpenAI's lightweight GPT-5 Mini model released on 7th August 2025"
        
class OpenAI_GPT5_nano(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5-nano",
            model_name="gpt-5-nano-2025-08-07",
            cost_per_input=0.0,
            cost_per_output=0.0,
            parallel_tool_call=True,
        )
        self.note = "OpenAI's ultra-lightweight GPT-5 Nano model released on 7th August 2025"
        
class OpenAI_GPT5_pro(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5-pro",
            model_name="gpt-5.2-pro-2025-12-11",
            cost_per_input=0.0,
            cost_per_output=0.0,
            parallel_tool_call=True,
        )
        self.note = "OpenAI's GPT-5 Pro model released on 11th December 2025"
        
class OpenAI_GPT5(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-5",
            model_name="gpt-5-2025-08-07",
            cost_per_input=0.0,
            cost_per_output=0.0,
            parallel_tool_call=True,
        )
        self.note = "OpenAI's GPT-5 model released on 7th August 2025"
        
class OpenAI_GPT41(OpenAIModel):
    def __init__(self):
        super().__init__(
            name="gpt-4.1",
            model_name="gpt-4.1-2025-04-14",
            cost_per_input=0.0,
            cost_per_output=0.0,
            parallel_tool_call=True,
        )
        self.note = "OpenAI's GPT-4.1 model released on 14th April 2025"