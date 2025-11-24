# Используем официальный образ Python 3.13
FROM python:3.13

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем netcat для проверки доступности БД
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv для управления зависимостями
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем файлы зависимостей
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости
RUN uv sync --locked

# Копируем код приложения
COPY . .

# Настройка entrypoint
RUN chmod +x entrypoint.sh

# Открываем порт
EXPOSE 8000

# Используем entrypoint для запуска приложения
ENTRYPOINT ["./entrypoint.sh"]

