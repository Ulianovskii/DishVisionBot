#!/bin/bash

# Корень проекта — папка, где лежит этот скрипт
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Что хотим выгрузить
TARGETS=(
  app/config_limits.py
  app/config.py
  app/main.py

  app/bot/handlers          # все хендлеры: main_menu, analysis, profile, payments, reports, admin, premium, common
  app/bot/keyboards.py
  app/bot/states.py
  app/bot/middlewares       # user middleware

  app/locales/ru            # buttons.py и texts.py

  app/prompts               # food_analysis и будущие промпты
  app/services              # gpt_client, limit_service, promo_service, user_service
  app/db                    # base, models, repositories

  db_migrations             # SQL-миграции

  docker-compose.yml
  Makefile
  requirements.txt
)

echo "=== DishVisionBot file export ==="
cd "$ROOT_DIR" || exit 1

for path in "${TARGETS[@]}"; do
    if [ -d "$path" ]; then
        # Папка — выводим все файлы внутри (python + sql + yaml и т.п.)
        find "$path" -type f \( -name "*.py" -o -name "*.sql" -o -name "*.yml" -o -name "*.yaml" \) | sort | while read -r file; do
            echo ""
            echo "===================="
            echo "=== FILE: $file ==="
            echo "===================="
            cat "$file"
            echo ""
        done
    elif [ -f "$path" ]; then
        # Одиночный файл
        echo ""
        echo "===================="
        echo "=== FILE: $path ==="
        echo "===================="
        cat "$path"
        echo ""
    else
        echo ""
        echo "=== SKIP: $path (not found) ==="
        echo ""
    fi
done

echo "=== END ==="
