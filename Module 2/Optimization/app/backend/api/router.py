from app.backend.api import form
from app.backend.api import openai, openrouter

def register_all_models() -> None:
    """
    Register all models.
    """
    form.register_model(openai.OpenAI_GPT52())
    form.register_model(openai.OpenAI_GPT5_mini())
    form.register_model(openai.OpenAI_GPT5_nano())
    form.register_model(openai.OpenAI_GPT5_pro())
    form.register_model(openai.OpenAI_GPT5())
    form.register_model(openai.OpenAI_GPT41())
    form.register_model(openrouter.OpenAI_OSS_120B())

    # Set a deterministic default once, without re-instantiating
    form.SELECTED_MODEL = form.MODEL_HUB.get("gpt-oss-120b")