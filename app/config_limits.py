# app/config_limits.py
"""
Глобальные настройки тарифов, лимитов и защит от злоупотреблений.

Все "магические числа" по лимитам, тайм-аутам и т.п. должны лежать здесь,
чтобы их не пришлось вылавливать по коду.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TariffConfig:
    """
    Настройки тарифов по ТЗ.
    """
    daily_photos: int            # Лимит анализов фото в день
    refinements_per_photo: int   # Лимит уточнений на одно фото


# ---- Тарифы ----

FREE_TARIFF = TariffConfig(
    daily_photos=5,          # Бесплатный: 5 фото/день
    refinements_per_photo=2, # Бесплатный: 2 уточнения на фото
)

PREMIUM_TARIFF = TariffConfig(
    daily_photos=20,         # Премиум: 15 фото/день
    refinements_per_photo=5, # Премиум: 5 уточнений на фото
)

# ---- Цены премиума в звёздах ----

STARS_PREMIUM_WEEK: int = 100
STARS_PREMIUM_MONTH: int = 250


PRICE_PER_ANALYSIS = {
    "price": 20,  # Количество звезд
    "number_of_analyses": 5  # Количество анализов, которое можно купить за эти звезды
}

# ---- Лимиты по сессии анализа фото ----

# Максимум текстовых сообщений к одному фото в STATE_PHOTO_COMMENT
PHOTO_SESSION_MAX_MESSAGES: int = 5

# Тайм-аут неактивности сессии анализа (в минутах), после которого
# мы считаем сессию истёкшей и просим прислать новое фото.
PHOTO_SESSION_TIMEOUT_MINUTES: int = 60


# ---- Антифлуд по промокодам ----
# (будем использовать на Этапе 2, но фиксируем сразу по ТЗ)

# Сколько подряд неверных попыток ввода промокода до бана
PROMO_MAX_ATTEMPTS_BEFORE_BAN: int = 10

# Длительности банов (в минутах) за 1-ю, 2-ю, 3-ю "серию" промахов
PROMO_BAN_MINUTES_FIRST: int = 30      # первая серия: 30 минут
PROMO_BAN_MINUTES_SECOND: int = 24 * 60  # вторая серия: 24 часа
PROMO_BAN_MINUTES_THIRD: int = 7 * 24 * 60  # третья серия: неделя





