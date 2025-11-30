#!/bin/bash

FILES=(
    "app/main.py"
    "app/db"
    "app/services"
    "app/bot/handlers"
    "app/settings.py"
)

echo "=== DishVisionBot file export ==="

for path in "${FILES[@]}"; do
    if [ -d "$path" ]; then
        # Папка — выводим рекурсивно
        find "$path" -type f -name "*.py" | while read file; do
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
    fi
done

echo "=== END ==="
