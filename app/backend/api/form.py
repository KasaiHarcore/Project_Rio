from __future__ import annotations

import sys
import threading
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import Any

from app.backend.utils.log import log_info, log_success
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

thread_cost = threading.local()


def _init_thread_cost():
    """Initialize thread-local cost tracking attributes if not already set."""
    if not hasattr(thread_cost, 'process_cost'):
        thread_cost.process_cost = 0.0
        thread_cost.process_input_tokens = 0
        thread_cost.process_output_tokens = 0

class Model(ABC):
    def __init__(
        self,
        name: str,
        cost_per_input: float,
        cost_per_output: float,
        parallel_tool_call: bool = False,
    ):
        self.chat_map = {}
        self.name: str = name
        # cost stats - zero for local models
        self.cost_per_input: float = cost_per_input
        self.cost_per_output: float = cost_per_output
        # whether the model supports parallel tool call
        self.parallel_tool_call: bool = parallel_tool_call
        self.vector_store = None

    @abstractmethod
    def check_api_key(self) -> str:
        raise NotImplementedError("abstract base class")

    @abstractmethod
    def setup(self) -> None:
        raise NotImplementedError("abstract base class")

    @abstractmethod
    def call(self, messages: list[dict], **kwargs):
        raise NotImplementedError("abstract base class")
    
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

    def calc_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculates the cost of a request based on the number of input/output tokens.
        """
        input_cost = self.cost_per_input * input_tokens
        output_cost = self.cost_per_output * output_tokens
        cost = input_cost + output_cost
        log_info(
            f"Model API request cost info: "
            f"input_tokens={input_tokens}, output_tokens={output_tokens}, cost={cost:.6f}"
        )
        return cost

    def get_overall_exec_stats(self):
        # Use getattr with defaults to handle thread-local storage across different threads
        input_tokens = getattr(thread_cost, 'process_input_tokens', 0)
        output_tokens = getattr(thread_cost, 'process_output_tokens', 0)
        cost = getattr(thread_cost, 'process_cost', 0.0)
        
        return {
            "model": self.name,
            "input_cost_per_token": self.cost_per_input,
            "output_cost_per_token": self.cost_per_output,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "total_cost": cost,
        }


MODEL_HUB = {}


def register_model(model: Model):
    global MODEL_HUB
    MODEL_HUB[model.name] = model


def get_all_model_names():
    return list(MODEL_HUB.keys())


SELECTED_MODEL: Model = None  # Initialize to None, set by register_all_models()


def set_model(model_name: str):
    global SELECTED_MODEL
    if model_name not in MODEL_HUB:
        raise ValueError(f"Invalid model name: {model_name}")
    SELECTED_MODEL = MODEL_HUB[model_name]

MODEL_TEMP: float = 0.0
MODEL_CHUNK_SIZE: int = 2056
MODEL_CHUNK_OVERLAP: int = 256