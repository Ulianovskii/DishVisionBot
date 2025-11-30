#!/bin/bash

# Корень проекта — папка, где лежит этот скрипт
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Что хотим выгрузить
TARGETS=(
  "app/main.py"
  "app/config.py"
  "app/config_limits.py"
  "app/bot"
  "app/db"
  "app/services"
  "app/locales/ru"
  "app/prompts"
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
