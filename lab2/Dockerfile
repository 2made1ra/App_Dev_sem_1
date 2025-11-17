# Используем официальный образ Python 3.13
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем uv для управления зависимостями
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем файлы зависимостей
COPY pyproject.toml ./

# Создаем виртуальное окружение и устанавливаем зависимости
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Копируем код приложения
COPY . .

# Создаем директорию для миграций (если нужно)
RUN mkdir -p app/migrations/versions

# Открываем порт
EXPOSE 8000

# Запускаем приложение
# Миграции применяются через docker-compose command
CMD [".venv/bin/python", "main.py"]

