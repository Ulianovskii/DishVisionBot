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

client = AsyncOpenAI(api_key=settings.openai_api_key)

DEFAULT_MODEL = "gpt-4o-mini"
AnalysisType = Literal["nutrition", "recipe"]


def _get_model_name() -> str:
    return getattr(settings, "openai_model", DEFAULT_MODEL)


def _build_message_content(
    analysis_type: AnalysisType,
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> list[dict]:
    """
    Контент для user-сообщения в chat.completions:
    content = [
      {"type": "text", "text": "..."},
      {"type": "image_url", "image_url": {"url": "..."}}
    ]
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

    comment = (comment or "").strip()
    if comment:
        text = f"{base_text}\n\nОписание от пользователя:\n{comment}"
    else:
        text = base_text

    parts: list[dict] = [
        {
            "type": "text",
            "text": text,
        }
    ]

    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        parts.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                },
            }
        )

    return parts


async def _call_gpt_with_vision(
    analysis_type: AnalysisType,
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> str:
    """
    Вызов chat.completions с картинкой + текстом.
    """
    model = _get_model_name()
    system_prompt = (
        SYSTEM_PROMPT_NUTRITION
        if analysis_type == "nutrition"
        else SYSTEM_PROMPT_RECIPE
    )

    logger.debug("Calling OpenAI Chat model=%s for %s", model, analysis_type)

    response = await client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": _build_message_content(
                    analysis_type=analysis_type,
                    image_bytes=image_bytes,
                    comment=comment,
                ),
            },
        ],
    )

    content = response.choices[0].message.content

    # content может быть строкой или списком сегментов
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                chunks.append(str(part["text"]))
            else:
                chunks.append(str(part))
        return "\n".join(chunks)

    return content or ""


async def analyze_nutrition(
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> str:
    return await _call_gpt_with_vision("nutrition", image_bytes, comment)


async def analyze_recipe(
    image_bytes: Optional[bytes],
    comment: Optional[str],
) -> str:
    return await _call_gpt_with_vision("recipe", image_bytes, comment)
