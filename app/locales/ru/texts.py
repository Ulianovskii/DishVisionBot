class RussianTexts:
    texts = {
        "send_photo_for_analysis": "📸 Отправьте фото еды для анализа",
        "help_text": "📖 Справка по использованию DishVisionBot (MVP). Здесь будет подробное описание функций позже.",
        "calories_plan_prompt": "🎯 Укажите дневной план калорий числом (от 0 до 10000).",
    }

    @classmethod
    def get(cls, key: str, **kwargs) -> str:
        text = cls.texts.get(key, f"Текст не найден: {key}")
        return text.format(**kwargs) if kwargs else text
