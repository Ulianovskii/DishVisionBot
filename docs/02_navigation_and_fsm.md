# 2. Навигация, кнопки и FSM

## 2.1. Кнопки интерфейса (локализация `ru`)

Ниже — согласованный перечень кнопок и их лейблов.  
Эти значения лежат в `app/locales/ru/buttons.py`.

```python
class RussianButtons:
    """Кнопки русского интерфейса"""

    buttons = {
        # Стартовая страница
        "start": "Начать",

        # Главная
        "analyze_food": "📸 Анализировать еду",
        "help": "Помощь",
        "profile": "Профиль",
        "reports": "Отчеты",
        "buy_premium": "Купить премиум",

        # Раздел анализа
        "nutrition": "Калорийность",
        "recipe": "Рецепт",
        "new_photo": "Новое фото",
        "back": "Главная",

        # Под меню анализа
        "ate_this": "Я это съел",
        "did_not_eat": "Я это не ел",

        # Под меню лимитов / преимуществ премиум
        "buy_premium": "Купить премиум",

        # Помощь
        "set_calorie_goal": "Установить цель по калориям",

        # Профиль
        "calorie_plan": "План калорий",

        # Оплата
        "buy_month_confirm": "Купить премиум на месяц",
        "buy_week_confirm": "Купить премиум на неделю",
        "enter_promo": "Ввести промокод",

        # Отчеты
        "report_day": "Отчет за день",
        "report_week": "Отчет за неделю",
        "report_month": "Отчет за месяц",

        # Админка
        "admin_statistics": "Статистика",
        "admin_manage_limits": "Управление лимитами",
        "admin_exit": "Выйти",

        # Управление лимитами
        "admin_sub_toggle_premium": "Установить режим премиум",
        "admin_sub_toggle_free": "Установить режим бесплатный",
        "admin_reset_own_limits": "Сбросить лимиты себе",
        "admin_reset_limits": "Сбросить лимиты пользователю",
        "admin_promo": "Промокод",

        # Статистика
        "stat_week": "За неделю",
        "stat_month": "За месяц",
        "stat_all_time": "За все время",
    }

    @classmethod
    def get(cls, key: str) -> str:
        return cls.buttons.get(key, f"Кнопка:{key}")
```

### 2.1.1. Кнопки по экранам

- **Стартовая страница**
  - `<label start>` — «Начать»

- **Главная страница**
  - `<label analyze_food>` — «📸 Анализировать еду»
  - `<label help>` — «Помощь»
  - `<label profile>` — «Профиль»
  - `<label reports>` — «Отчеты»
  - `<label buy_premium>` — «Купить премиум» (только для бесплатного тарифа)

- **Раздел анализа блюда**
  - `<label nutrition>` — «Калорийность»
  - `<label recipe>` — «Рецепт»
  - `<label new_photo>` — «Новое фото»
  - `<label back>` — «Главная»

- **Подстрочное меню под анализом (после ответа GPT)**
  - `<label ate_this>` — «Я это съел»
  - `<label did_not_eat>` — «Я это не ел»

- **Подстрочное меню под сообщением о лимитах / преимуществах премиума**
  - `<label buy_premium>` — «Купить премиум»

- **Помощь**
  - `<label set_calorie_goal>` — «Установить цель по калориям»
  - `<label reports>` — «Отчеты»
  - `<label back>` — «Главная»
  - `<label buy_premium>` — «Купить премиум»

- **Профиль**
  - `<label analyze_food>` — «📸 Анализировать еду»
  - `<label help>` — «Помощь»
  - `<label reports>` — «Отчеты»
  - `<label calorie_plan>` — «План калорий»
  - `<label buy_premium>` — «Купить премиум»

- **Оплата**
  - `<label buy_month_confirm>` — «Купить премиум на месяц»
  - `<label buy_week_confirm>` — «Купить премиум на неделю»
  - `<label enter_promo>` — «Ввести промокод»
  - `<label back>` — «Главная»

- **Отчеты**
  - `<label report_day>` — «Отчет за день»
  - `<label report_week>` — «Отчет за неделю»
  - `<label report_month>` — «Отчет за месяц»
  - `<label back>` — «Главная»

- **Админка**
  - `<label admin_statistics>` — «Статистика»
  - `<label admin_manage_limits>` — «Управление лимитами»
  - `<label admin_exit>` — «Выйти»

- **Управление лимитами**
  - `<label admin_sub_toggle_premium>` — «Установить режим премиум»
  - `<label admin_sub_toggle_free>` — «Установить режим бесплатный»
  - `<label admin_reset_own_limits>` — «Сбросить лимиты себе»
  - `<label admin_reset_limits>` — «Сбросить лимиты пользователю»
  - `<label admin_promo>` — «Промокод»
  - `<label back>` — «Вернуться»

- **Статистика (админ)**
  - `<label stat_week>` — «За неделю»
  - `<label stat_month>` — «За месяц»
  - `<label stat_all_time>` — «За все время»
  - `<label back>` — «Вернуться»


## 2.2. FSM (Finite State Machine)

FSM используется для управления тем, **как интерпретировать текстовые сообщения** пользователя в зависимости от текущего режима.

```python
# FSM состояния
STATE_STANDARD = "standard_mode"
STATE_PHOTO_COMMENT = "photo_comment_input"
STATE_PROMO = "promo_input"
STATE_CALORIES_PLAN = "calories_plan_input"
STATE_ADMIN = "admin_mode"
STATE_LIMIT_RESET = "limit_reset_input"
STATE_PROMO_GENERATE = "promo_generate_input"
```

### 2.2.1. Описание состояний

- `STATE_STANDARD` (**standard_mode**)  
  Стандартный режим. Пользователь может:
  - Нажимать любые кнопки меню
  - Отправлять фото (перевод в `STATE_PHOTO_COMMENT`)
  - Отправить текст, не относящийся к ожидаемому вводу → бот показывает подсказку (`help_text` / упрощенная подсказка).

- `STATE_PHOTO_COMMENT` (**photo_comment_input**)  
  Режим анализа блюда:
  - Пользователь прислал фото
  - Бот собирает комментарии к фото (уточнения по блюду)
  - Лимиты:
    - Общее число сообщений к фото
    - Число «уточнений» для повторных вызовов GPT
  - Выход:
    - По нажатию `<label nutrition>` или `<label recipe>` (после анализа)
    - По нажатию `<label new_photo>` (новая сессия анализа)
    - По истечению времени сессии
    - По превышению лимитов

- `STATE_PROMO` (**promo_input**)  
  Режим ввода промокода:
  - Вход: кнопка `<label enter_promo>`
  - Все текстовые сообщения интерпретируются как промокоды
  - Есть лимиты на количество неверных попыток и баны по времени
  - Выход: успешная активация, нажатие любой другой кнопки, истечение бана.

- `STATE_CALORIES_PLAN` (**calories_plan_input**)  
  Режим ввода дневного плана калорий:
  - Вход: `<label calorie_plan>` или `<label set_calorie_goal>`
  - Ожидается одно число 0–10000
  - 0 — сброс плана, план не учитывается в отчетах
  - Выход: успешный ввод, нажатие другой кнопки.

- `STATE_ADMIN` (**admin_mode**)  
  Режим администрирования:
  - Вход: команда `/superadmin` + проверка user_id
  - Доступны кнопки админки: статистика, управление лимитами, выйти
  - Выход: по кнопке `<label admin_exit>` или /start.

- `STATE_LIMIT_RESET` (**limit_reset_input**)  
  Подрежим `STATE_ADMIN`:
  - Вход: `<label admin_reset_limits>`
  - Ожидается ID пользователя для сброса лимитов
  - Выход: удачный/неудачный сброс + возврат в `STATE_ADMIN`.

- `STATE_PROMO_GENERATE` (**promo_generate_input**)  
  Подрежим `STATE_ADMIN`:
  - Вход: `<label admin_promo>`
  - Ожидается число 1–10 — сколько уникальных промокодов сгенерировать
  - Выход: после генерации — возврат в `STATE_ADMIN`.

