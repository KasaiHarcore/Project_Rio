"""
Model registry and shared LLM utilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from utils.log import log_info, log_success
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


class Model(ABC):
    def __init__(
        self,
        name: str,
        cost_per_input: float,
        cost_per_output: float,
    ):
        self.name: str = name
        self.cost_per_input: float = cost_per_input
        self.cost_per_output: float = cost_per_output

    @abstractmethod
    def check_api_key(self) -> str:
        raise NotImplementedError("abstract base class")

    @abstractmethod
    def setup(self) -> None:
        raise NotImplementedError("abstract base class")

    def stream(
        self,
        *,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
        ai_prompt: str | None = None,
        messages: list[BaseMessage] | None = None,
        **kwargs,
    ) -> Iterable[str]:
        """Stream tokens from the model.

        Override in subclasses that support streaming.
        """
        raise NotImplementedError("Streaming is not supported by this model")

    def format_messages(
        self,
        *,
        system_prompt: str,
        ai_prompt: str = None,
        user_prompt: str,
    ) -> list[BaseMessage]:
        """
        Build chat messages from system/user
        """
        messages: list[BaseMessage] = []

        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
            log_info("System Prompt detected")

        if ai_prompt:
            messages.append(AIMessage(content=ai_prompt))
            log_info("AI output format detected")

        messages.append(HumanMessage(content=user_prompt))
        log_success("Prompt Fetch Successfully")
        return messages

    def get_overall_exec_stats(self):
        return {
            "model": self.name,
            "input_cost_per_token": self.cost_per_input,
            "output_cost_per_token": self.cost_per_output,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }


MODEL_HUB = {}


def register_model(model: Model):
    global MODEL_HUB
    MODEL_HUB[model.name] = model


def get_all_model_names():
    return list(MODEL_HUB.keys())


SELECTED_MODEL: Model = None

def set_model(model_name: str):
    global SELECTED_MODEL
    if model_name not in MODEL_HUB:
        raise ValueError(f"Invalid model name: {model_name}")
    SELECTED_MODEL = MODEL_HUB[model_name]
    
MODEL_TEMP: float = 0.0