"""Model registration utilities."""

from backend.services.llm import form
from backend.services.llm import openai_client, openrouter_client


def register_all_models() -> None:
    """
    Register all models.
    """
    form.register_model(openai_client.OpenAI_GPT52())
    form.register_model(openai_client.OpenAI_GPT5_mini())
    form.register_model(openai_client.OpenAI_GPT5_nano())
    form.register_model(openai_client.OpenAI_GPT5_pro())
    form.register_model(openai_client.OpenAI_GPT5())
    form.register_model(openai_client.OpenAI_GPT41())
    form.register_model(openrouter_client.OpenAI_OSS_120B())

    # Set a deterministic default once, without re-instantiating
    form.SELECTED_MODEL = form.MODEL_HUB.get("gpt-oss-120b")
