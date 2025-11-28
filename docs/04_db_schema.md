# 4. Структура БД (черновой вариант)

База данных — PostgreSQL. Ниже приведена примерная схема таблиц.

## 4.1. Таблица users

Хранит базовую информацию о пользователях.

```sql
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    is_premium      BOOLEAN NOT NULL DEFAULT FALSE,
    premium_until   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 4.2. Таблица user_limits

Лимиты и статистика использования за день.

```sql
CREATE TABLE user_limits (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date                DATE NOT NULL,
    photos_used         INT NOT NULL DEFAULT 0,
    refinements_used    INT NOT NULL DEFAULT 0,
    CONSTRAINT user_limits_unique UNIQUE (user_id, date)
);
```

- `photos_used` — сколько фото было проанализировано за день.
- `refinements_used` — сколько уточнений сделано за день (если необходимо считать глобально).

## 4.3. Таблица meals

Фиксация «я это съел» по каждому блюду.

```sql
CREATE TABLE meals (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    eaten_at        TIMESTAMPTZ NOT NULL,      -- время, когда пользователь нажал "Я это съел"
    title           TEXT NOT NULL,             -- название блюда
    weight_grams    INT,                       -- вес в граммах (может быть NULL)
    calories        INT,                       -- калории на порцию
    proteins        REAL,
    fats            REAL,
    carbs           REAL,
    source_message_id BIGINT,                  -- id сообщения Telegram (опционально)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 4.4. Таблица calorie_plans

План по калориям в день.

```sql
CREATE TABLE calorie_plans (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    daily_target    INT NOT NULL,             -- 0..10000
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

- Можно хранить только текущий план (одна строка на пользователя) или вести историю изменений.

## 4.5. Таблица promo_codes

Промокоды для активации премиум подписки.

```sql
CREATE TABLE promo_codes (
    id              BIGSERIAL PRIMARY KEY,
    code            TEXT UNIQUE NOT NULL,
    days            INT NOT NULL,                  -- на сколько дней даёт премиум
    max_activations INT NOT NULL DEFAULT 1,        -- количество активаций (обычно 1)
    activations     INT NOT NULL DEFAULT 0,
    expires_at      TIMESTAMPTZ,                   -- дата истечения промокода (может быть NULL)
    created_by      BIGINT,                        -- admin user id (опционально)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 4.6. Таблица promo_code_activations

Запись факта использования промокода.

```sql
CREATE TABLE promo_code_activations (
    id              BIGSERIAL PRIMARY KEY,
    promo_code_id   BIGINT NOT NULL REFERENCES promo_codes(id) ON DELETE CASCADE,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 4.7. Таблица promo_bans

Блокировка ввода промокодов при злоупотреблениях.

```sql
CREATE TABLE promo_bans (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    banned_until    TIMESTAMPTZ NOT NULL,
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 4.8. Таблица admin_users

Список администраторов (опционально, можно хранить в .env).

```sql
CREATE TABLE admin_users (
    id              BIGSERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 4.9. Таблица gpt_usage_stats

Статистика расходов токенов GPT по пользователям и дням.

```sql
CREATE TABLE gpt_usage_stats (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE SET NULL,
    date            DATE NOT NULL,
    tokens_prompt   INT NOT NULL DEFAULT 0,
    tokens_completion INT NOT NULL DEFAULT 0,
    cost_usd        NUMERIC(10,4) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT gpt_usage_unique UNIQUE (user_id, date)
);
```

Этого набора таблиц достаточно для реализации первой версии продукта, отчетов и админской статистики.
