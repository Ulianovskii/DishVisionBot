import asyncio

from openai import AsyncOpenAI

from app.config import settings


class GPTClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(self, prompt: str, *, user_id: str | None = None) -> str:
        # TODO: заменить на реальный вызов модели согласно 05_openai_prompts.md
        await asyncio.sleep(0.1)
        return "Заглушка ответа GPT"


gpt_client = GPTClient()
