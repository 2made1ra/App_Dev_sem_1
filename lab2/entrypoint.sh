#!/bin/bash

set -e

# Ожидание готовности базы данных
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done

# Применение миграций
cd app && uv run alembic upgrade head && cd ..

# Запуск приложения
exec "$@"

