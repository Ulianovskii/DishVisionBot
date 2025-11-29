# app/services/gpt_client.py

import base64
import logging
from typing import Literal, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.prompts.food_analysis import (
    SYSTEM_PROMPT_NUTRITION,
    SYSTEM_PROMPT_RECIPE,
)

logger = logging.getLogger(__name__)

# Async-клиент OpenAI
client = AsyncOpenAI(api_key=settings.openai_api_key)

DEFAULT_MODEL = "gpt-4o-mini"
AnalysisType = Literal["nutrition", "recipe"]


def _get_model_name() -> str:
    """
    Если в Settings есть openai_model — используем его, иначе дефолт.
    """
    return getattr(settings, "openai_model", DEFAULT_MODEL)


def _build_user_content(
    analysis_type: AnalysisType,
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> list[dict]:
    """
    Собираем content для Responses API:
    - input_text: инструкция + комментарий пользователя
    - input_image: фото в base64
    """
    if analysis_type == "nutrition":
        base_text = (
            "Проанализируй блюда на фото: оцени общую калорийность и БЖУ всех блюд "
            "и выведи ответ строго в формате из системного промпта."
        )
    else:
        base_text = (
            "Составь подробные рецепты для блюд на фото по инструкциям системного промпта."
        )

    if comment:
        text = f"{base_text}\n\nОписание от пользователя:\n{comment}"
    else:
        text = base_text

    parts: list[dict] = [
        {
            "type": "input_text",
            "text": text,
        }
    ]

    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        parts.append(
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{b64}",
            }
        )

    return parts


async def _call_gpt_with_vision(
    analysis_type: AnalysisType,
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> str:
    """
    Общий вызов Responses API с картинкой + текстом.
    """
    model = _get_model_name()
    system_prompt = (
        SYSTEM_PROMPT_NUTRITION
        if analysis_type == "nutrition"
        else SYSTEM_PROMPT_RECIPE
    )

    logger.debug("Calling OpenAI Responses model=%s for %s", model, analysis_type)

    input_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": _build_user_content(analysis_type, image_bytes, comment),
        },
    ]

    response = await client.responses.create(
        model=model,
        input=input_messages,
    )

    # Быстрый путь, если доступен output_text
    text = getattr(response, "output_text", None)
    if text:
        return text

    # Запасной путь — собрать текст вручную
    output = getattr(response, "output", None)
    if not output:
        return ""

    chunks: list[str] = []
    for item in output:
        if hasattr(item, "content") and item.content:
            for c in item.content:
                if hasattr(c, "text") and c.text:
                    chunks.append(c.text)

    return "\n".join(chunks)


async def analyze_nutrition(
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> str:
    """
    Анализ калорийности по фото + тексту.
    """
    return await _call_gpt_with_vision("nutrition", image_bytes, comment)


async def analyze_recipe(
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> str:
    """
    Анализ рецепта по фото + тексту.
    """
    return await _call_gpt_with_vision("recipe", image_bytes, comment)
