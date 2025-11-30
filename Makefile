SHELL := /bin/bash

.PHONY: run stop restart logs install venv clean check-env setup help \
        test test-gpt test-bot test-coverage test-api \
        docker-up docker-down docker-logs docker-db \
        deploy safe-run start stop-all install-full reinstall check-docker dev

# ============================
# 🐳 Docker / БД
# ============================

# Поднять все контейнеры из docker-compose.yml (в т.ч. db)
docker-up:
	docker-compose up -d
	@echo "✅ Docker контейнеры запущены"

# Остановить все контейнеры из docker-compose.yml
docker-down:
	docker-compose down
	@echo "✅ Docker контейнеры остановлены"

# Логи сервиса db
docker-logs:
	docker-compose logs -f db

# Зайти в psql внутри контейнера db
docker-db:
	docker-compose exec db psql -U foodlens_user -d foodlens

# Проверка, что Docker-контейнеры подняты, иначе поднять
check-docker:
	@if ! docker-compose ps | grep -q "Up"; then \
		echo "🐳 Запускаем Docker контейнеры..."; \
		docker-compose up -d; \
		sleep 5; \
	fi
	@echo "✅ Docker контейнеры запущены"

# ============================
# 🧱 Виртуальное окружение и зависимости
# ============================

# Создание и настройка виртуального окружения
setup:
	python -m venv .venv
	@echo "✅ Виртуальное окружение создано в .venv"
	@echo "🤖 Для активации выполните: source .venv/bin/activate"
	@echo "📦 Затем установите зависимости: make install"

# Установка основных зависимостей
install:
	@if [ -d ".venv" ]; then \
		source .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -r requirements.txt; \
		if [ $$? -eq 0 ]; then \
			echo "✅ Зависимости установлены"; \
		else \
			echo "❌ Ошибка установки зависимостей"; \
			exit 1; \
		fi \
	else \
		echo "❌ Виртуальное окружение не найдено. Сначала выполните: make setup"; \
		exit 1; \
	fi

# Установка всех зависимостей (включая тестовые)
install-full: install
	source .venv/bin/activate && pip install pytest pytest-asyncio pytest-cov watchdog
	@echo "✅ Все зависимости (включая тестовые) установлены"

# Полная переустановка (ядерный вариант)
reinstall: clean
	rm -rf .venv
	make setup
	make install-full

# Проверка наличия .env и ключей
check-env:
	@if [ ! -f ".env" ]; then \
		echo "❌ Файл .env не найден. Скопируйте .env.example и заполните значения."; \
		exit 1; \
	fi
	@if ! grep -q "BOT_TOKEN=" .env || grep -q "BOT_TOKEN=your_telegram_bot_token_here" .env; then \
		echo "❌ Ошибка: BOT_TOKEN не настроен в .env файле!"; \
		echo "   Получите токен у @BotFather и добавьте в .env"; \
		exit 1; \
	fi
	@if ! grep -q "OPENAI_API_KEY=" .env || grep -q "OPENAI_API_KEY=your_openai_api_key_here" .env; then \
		echo "❌ Ошибка: OPENAI_API_KEY не настроен в .env файле!"; \
		echo "   Получите ключ на platform.openai.com и добавьте в .env"; \
		exit 1; \
	fi
	@echo "✅ Окружение настроено корректно"

# Проверка наличия .venv
check-venv:
	@if [ ! -d ".venv" ]; then \
		echo "❌ Виртуальное окружение не найдено"; \
		echo "🤖 Выполните: make setup"; \
		exit 1; \
	fi

# ============================
# 🚀 Запуск бота
# ============================

# Обычный запуск бота (с проверкой .env, venv и Docker/БД)
run: check-env check-venv check-docker
	source .venv/bin/activate && python -m app.main

# Запуск с авто-перезагрузкой при изменениях кода
dev: check-env check-venv check-docker
	@if ! ( source .venv/bin/activate && python -c "import watchdog" ) 2>/dev/null; then \
		echo "📦 Устанавливаем watchdog..."; \
		source .venv/bin/activate && pip install watchdog; \
	fi
	source .venv/bin/activate && watchmedo auto-restart --pattern="*.py" --recursive -- python -m app.main

# Остановка бота
stop:
	pkill -f "python.*app.main" || true
	@echo "✅ Бот остановлен"

# Перезапуск бота
restart: stop
	sleep 2
	make run

# Полный запуск (Docker + бот)
start: docker-up run

# Остановка всего (бот + Docker)
stop-all: stop docker-down

# Просмотр логов (если сделаешь логирование в файл)
logs:
	tail -f bot.log 2>/dev/null || echo "📝 Лог-файл не найден. Запустите бота сначала."

# Активация venv в отдельной shell-сессии
venv:
	@if [ -d ".venv" ]; then \
		source .venv/bin/activate && bash; \
	else \
		echo "❌ Виртуальное окружение не найдено. Выполните: make setup"; \
	fi

# ============================
# 🧪 Тестирование
# ============================

# Проверка тестовых зависимостей
check-test-deps: check-venv
	@if ! ( source .venv/bin/activate && python -c "import pytest" ) 2>/dev/null; then \
		echo "📦 Устанавливаем тестовые зависимости..."; \
		source .venv/bin/activate && pip install pytest pytest-asyncio; \
	fi

test: check-env check-venv check-test-deps
	@if [ ! -d "tests" ]; then \
		echo "❌ Папка tests не найдена"; \
		exit 1; \
	fi
	source .venv/bin/activate && python -m pytest tests/ -v

test-gpt: check-env check-venv check-test-deps
	@if [ ! -f "tests/test_gpt_analyzer.py" ]; then \
		echo "❌ Файл tests/test_gpt_analyzer.py не найден"; \
		exit 1; \
	fi
	source .venv/bin/activate && python -m pytest tests/test_gpt_analyzer.py -v

test-bot: check-env check-venv check-test-deps
	@if [ ! -f "tests/test_bot_handlers.py" ]; then \
		echo "❌ Файл tests/test_bot_handlers.py не найден"; \
		exit 1; \
	fi
	source .venv/bin/activate && python -m pytest tests/test_bot_handlers.py -v

test-coverage: check-env check-venv check-test-deps
	@if ! ( source .venv/bin/activate && python -c "import pytest_cov" ) 2>/dev/null; then \
		echo "📦 Устанавливаем pytest-cov..."; \
		source .venv/bin/activate && pip install pytest-cov; \
	fi
	source .venv/bin/activate && python -m pytest tests/ --cov=app --cov-report=html

# Быстрый тест API (без pytest)
test-api: check-env check-venv
	@if [ ! -f "tests/quick_test.py" ]; then \
		echo "❌ Файл tests/quick_test.py не найден"; \
		exit 1; \
	fi
	source .venv/bin/activate && python tests/quick_test.py

# ============================
# 🧼 Утилиты
# ============================

# Очистка кэша Python
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Кэш очищен"

# ============================
# 🚢 Деплой / безопасный запуск
# ============================

# Безопасный запуск: сначала тесты, потом бот
safe-run: check-env check-venv test
	@echo "✅ Все тесты пройдены, запускаем бота..."
	make run

# "Деплой" сейчас = просто прогоны тестов перед выкладкой
# (run не цепляем, чтобы команда не блокировалась)
deploy: check-env check-venv test
	@echo "✅ Тесты пройдены. Можно деплоить на прод (через systemd/Docker)."

# ============================
# ℹ️ Help
# ============================

help:
	@echo "🍱 DishVisionBot - Доступные команды:"
	@echo ""
	@echo "🏗️  Установка:"
	@echo "  make setup        - Создать виртуальное окружение (.venv)"
	@echo "  make install      - Установить основные зависимости"
	@echo "  make install-full - Установить все зависимости (включая тесты)"
	@echo "  make reinstall    - Полная переустановка (очистка + venv + зависимости)"
	@echo ""
	@echo "🚀 Запуск:"
	@echo "  make run          - Запуск бота (с проверкой .env, venv, Docker/БД)"
	@echo "  make dev          - Запуск с авто-перезагрузкой (watchdog)"
	@echo "  make restart      - Перезапуск бота"
	@echo "  make stop         - Остановка бота"
	@echo "  make start        - Поднять Docker и запустить бота"
	@echo "  make stop-all     - Остановить бота и Docker"
	@echo ""
	@echo "🧪 Тестирование:"
	@echo "  make test         - Все тесты"
	@echo "  make test-gpt     - Тесты GPT-анализатора"
	@echo "  make test-bot     - Тесты обработчиков бота"
	@echo "  make test-api     - Быстрый тест API (скриптом)"
	@echo "  make test-coverage - Тесты с покрытием кода"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-up    - Поднять контейнеры (docker-compose up -d)"
	@echo "  make docker-down  - Остановить контейнеры"
	@echo "  make docker-logs  - Логи БД (сервис db)"
	@echo "  make docker-db    - Зайти в psql внутри db"
	@echo ""
	@echo "🔧 Утилиты:"
	@echo "  make logs         - Просмотр локального лог-файла бота (если есть)"
	@echo "  make venv         - Открыть shell с активным .venv"
	@echo "  make clean        - Очистка кэша Python"
	@echo "  make check-env    - Проверка .env и токенов"
	@echo "  make help         - Эта справка"
	@echo ""
	@echo "🚢 Деплой / проверка:"
	@echo "  make safe-run     - Тесты + запуск бота"
	@echo "  make deploy       - Только прогон тестов перед выкладкой"
