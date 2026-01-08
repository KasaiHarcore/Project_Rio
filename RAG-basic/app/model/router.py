from app.model import form
from app.api import openai, openrouter

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

    # register default model as selected
    form.SELECTED_MODEL = openrouter.OpenAI_OSS_120B()