#!/bin/bash

# Корень проекта — папка, где лежит этот скрипт
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Что хотим выгрузить
TARGETS=(
app/config_limits.py
app/bot/handlers/main_menu.py
app/bot/handlers/analysis.py
app/bot/handlers/premium.py
app/bot/handlers/profile.py
app/bot/handlers/admin.py
app/bot/keyboards.py
app/bot/states.py
app/locales/ru/buttons.py
app/locales/ru/texts.py
app/services/limit_service.py
app/services/user_service.py
app/db/models.py
app/main.py
)

echo "=== DishVisionBot file export ==="
cd "$ROOT_DIR" || exit 1

for path in "${TARGETS[@]}"; do
    if [ -d "$path" ]; then
        # Папка — выводим все Python-файлы внутри
        find "$path" -type f -name "*.py" | sort | while read -r file; do
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
