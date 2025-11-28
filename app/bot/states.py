from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """
    Основные пользовательские состояния по ТЗ.
    """

    STANDARD = State()          # Главное меню / базовое состояние
    PHOTO_COMMENT = State()     # Фото + комментарий, выбор nutrition/recipe
    PROMO = State()             # Ввод промокода
    CALORIES_PLAN = State()     # Ввод плана калорий
    ADMIN = State()             # Главное состояние админ-меню
    LIMIT_RESET = State()       # Сброс лимитов (админ)
    PROMO_GENERATE = State()    # Генерация промокодов (админ)
