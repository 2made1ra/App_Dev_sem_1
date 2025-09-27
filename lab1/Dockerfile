# Подтягиваем образ postgres
FROM postgres:17.6-bookworm

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем переменные окружения
ENV POSTGRES_USER=admin
ENV POSTGRES_PASSWORD=admin
ENV POSTGRES_DB=postgres

# Копируем скрипт инициализации базы данных
COPY . .

# Открываем порт 5432
EXPOSE 5432

# Запускаем postgres
CMD ["postgres"]