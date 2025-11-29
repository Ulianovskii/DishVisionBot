import logging

from openai import AsyncOpenAI

from app.config import settings
from app.prompts.food_analysis import (
    SYSTEM_PROMPT_NUTRITION,
    SYSTEM_PROMPT_RECIPE,
)

logger = logging.getLogger(__name__)

# Базовый async-клиент OpenAI
client = AsyncOpenAI(api_key=settings.openai_api_key)

# Модель по умолчанию (можно потом вынести в settings)
DEFAULT_MODEL = "gpt-4o-mini"


def _get_model_name() -> str:
    """
    Если потом в Settings добавим поле openai_model — используем его.
    Пока безопасно подхватываем его если есть, иначе дефолт.
    """
    return getattr(settings, "openai_model", DEFAULT_MODEL)


def _build_user_message(comment: str | None, analysis_type: str) -> str:
    """
    Собираем текст user-сообщения для GPT на основе комментария пользователя
    и типа анализа (nutrition / recipe).
    """
    comment = (comment or "").strip()

    if analysis_type == "nutrition":
        base = (
            "Проанализируй еду по описанию ниже: оцени общую калорийность и БЖУ "
            "всех блюд и выведи ответ строго в формате из системного промпта."
        )
    else:
        base = (
            "Составь подробный рецепт (или несколько рецептов) по описанию блюда ниже. "
            "Если блюд несколько, опиши их по отдельности, строго следуя формату системного промпта."
        )

    if comment:
        return f"{base}\n\nОписание от пользователя:\n{comment}"
    else:
        # Теоретически не должно быть пустым, но на всякий случай
        return base


async def _call_chat_gpt(system_prompt: str, user_text: str) -> str:
    """
    Общая функция вызова Chat Completions.
    """
    model = _get_model_name()
    logger.debug("Calling OpenAI model=%s", model)

    response = await client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )

    # Берём первый вариант ответа
    content = response.choices[0].message.content
    if isinstance(content, list):
        # на всякий случай, если библиотека вернёт массив объектов
        text_parts = [
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        ]
        return "\n".join(text_parts)
    return content or ""


async def analyze_nutrition_by_text(comment: str | None) -> str:
    """
    Анализ калорийности / БЖУ по текстовому описанию.
    (Фото пока не используем, только комментарий.)
    """
    user_text = _build_user_message(comment, analysis_type="nutrition")
    return await _call_chat_gpt(SYSTEM_PROMPT_NUTRITION, user_text)


async def analyze_recipe_by_text(comment: str | None) -> str:
    """
    Восстановление рецепта по текстовому описанию.
    """
    user_text = _build_user_message(comment, analysis_type="recipe")
    return await _call_chat_gpt(SYSTEM_PROMPT_RECIPE, user_text)
