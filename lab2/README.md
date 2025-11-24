# Лабораторная работа 5

Веб-приложение на базе фреймворка Litestar с использованием Dependency Injection и SQLAlchemy ORM для работы с пользователями.

## Оглавление

- [Быстрый старт](#быстрый-старт)
- [Установка и запуск](#установка-и-запуск)
  - [Вариант 1: Запуск через Docker Compose (Рекомендуется)](#вариант-1-запуск-через-docker-compose-рекомендуется)
  - [Вариант 2: Локальный запуск (для разработки)](#вариант-2-локальный-запуск-для-разработки)
- [Доступ к сервисам](#доступ-к-сервисам)
- [API Документация](#api-документация)
- [API Эндпоинты](#api-эндпоинты)
  - [Получить пользователя по ID](#получить-пользователя-по-id)
  - [Получить список пользователей](#получить-список-пользователей)
  - [Создать пользователя](#создать-пользователя)
  - [Обновить пользователя](#обновить-пользователя)
  - [Удалить пользователя](#удалить-пользователя)
- [Разработка](#разработка)
  - [Линтеры и форматеры](#линтеры-и-форматеры)
  - [Работа с Docker](#работа-с-docker)
  - [Доступ к базе данных](#доступ-к-базе-данных)
- [Структура данных](#структура-данных)
- [Обработка ошибок](#обработка-ошибок)

## Быстрый старт

```bash
# 1. Создайте .env файл (см. раздел "Установка и запуск")
# 2. Запустите всё одной командой:
docker compose up --build

# 3. Приложение доступно по адресу:
# http://localhost:8000
# http://localhost:8000/docs (API документация)
```

## Установка и запуск

### Вариант 1: Запуск через Docker Compose (Рекомендуется)
#### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd lab2
```

#### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=lab_db2

PGADMIN_DEFAULT_EMAIL=admin@lab2.com
PGADMIN_DEFAULT_PASSWORD=admin

DB_HOST=db
DB_PORT=5432
HOST=0.0.0.0
PORT=8000
```

> **Примечание:** `DATABASE_URL` для контейнера настраивается автоматически в `docker-compose.yml`. Переменные `DB_HOST` и `DB_PORT` используются в `entrypoint.sh` для ожидания готовности базы данных.

#### 3. Сборка и запуск всех сервисов

```bash
# Сборка образа и запуск
docker compose up --build

# Или в фоновом режиме
docker compose up --build -d
```

Эта команда автоматически:
- Соберёт Docker образ приложения (используя `Dockerfile`)
- Запустит PostgreSQL базу данных
- Запустит PgAdmin
- Применит миграции базы данных через `entrypoint.sh`
- Запустит веб-приложение

**Примечание:** При первом запуске или при изменении `Dockerfile` используйте флаг `--build` для пересборки образа. Скрипт `entrypoint.sh` автоматически ожидает готовности базы данных и применяет миграции перед запуском приложения.

#### 4. Проверка статуса

```bash
docker compose ps
```

Все сервисы должны быть в статусе `Up`:
- `app_lab3` - веб-приложение на порту `8000`
- `db_postgres_lab2` - PostgreSQL на порту `5433`
- `pgadmin4_lab2` - PgAdmin на порту `8081`

#### 5. Просмотр логов

```bash
# Все логи
docker compose logs -f

# Только приложение
docker compose logs -f app

# Только база данных
docker compose logs -f db
```

#### 6. Остановка сервисов

```bash
docker compose down
```

Для полной очистки (включая volumes):

```bash
docker compose down -v
```

---

### Вариант 2: Локальный запуск (для разработки)

без докера

#### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd lab2
```

#### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=lab_db2

PGADMIN_DEFAULT_EMAIL=admin@lab2.com
PGADMIN_DEFAULT_PASSWORD=admin

DATABASE_URL=postgresql+asyncpg://admin:admin@localhost:5433/lab_db2
```

#### 3. Установка зависимостей

```bash
uv sync
```

#### 4. Запуск базы данных

```bash
docker compose up -d db pgadmin
```

Это запустит только:
- PostgreSQL на порту `5433`
- PgAdmin на порту `8081`

#### 5. Применение миграций

```bash
cd app
../.venv/bin/alembic upgrade head
cd ..
```

#### 6. Запуск приложения

```bash
python main.py
```

Приложение будет доступно по адресу: `http://localhost:8000`

---

### Доступ к сервисам

После запуска приложение и сервисы будут доступны по следующим адресам:

- **Веб-приложение**: http://localhost:8000
- **API документация (Swagger)**: http://localhost:8000/docs
- **PgAdmin**: http://localhost:8081
- **PostgreSQL**: localhost:5433

## API Документация

После запуска приложения доступна интерактивная документация:

- **Swagger UI**: http://localhost:8000/docs
- **OpenAPI JSON**: http://localhost:8000/schema/openapi.json

## API Эндпоинты

### Получить пользователя по ID

```http
GET /users/{user_id}
```

**Параметры:**
- `user_id` (int, path) - ID пользователя (должен быть > 0)

**Ответ:**
- `200 OK` - Пользователь найден
- `404 Not Found` - Пользователь не найден

**Пример:**
```bash
curl http://localhost:8000/users/1
```

### Получить список пользователей

```http
GET /users?count=10&page=1
```

**Query параметры:**
- `count` (int, optional) - Количество записей на странице (1-100, по умолчанию 10)
- `page` (int, optional) - Номер страницы (≥1, по умолчанию 1)

**Ответ:**
```json
{
  "users": [
    {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com",
      "description": "Software developer",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-02T10:00:00"
    }
  ],
  "total": 25
}
```

**Пример:**
```bash
curl "http://localhost:8000/users?count=5&page=2"
```

### Создать пользователя

```http
POST /users
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "username": "jane_doe",
  "email": "jane@example.com",
  "description": "Designer"
}
```

**Ответ:**
- `201 Created` - Пользователь создан
- `400 Bad Request` - Ошибка валидации (email или username уже существует)
- `422 Unprocessable Entity` - Невалидные данные

**Пример:**
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jane_doe",
    "email": "jane@example.com",
    "description": "Designer"
  }'
```

### Обновить пользователя

```http
PUT /users/{user_id}
Content-Type: application/json
```

**Параметры:**
- `user_id` (int, path) - ID пользователя

**Тело запроса (все поля опциональные):**
```json
{
  "email": "newemail@example.com"
}
```

**Ответ:**
- `200 OK` - Пользователь обновлен
- `404 Not Found` - Пользователь не найден
- `400 Bad Request` - Email или username уже существует
- `422 Unprocessable Entity` - Невалидные данные

**Пример:**
```bash
curl -X PUT http://localhost:8000/users/1 \
  -H "Content-Type: application/json" \
  -d '{"email": "newemail@example.com"}'
```

### Удалить пользователя

```http
DELETE /users/{user_id}
```

**Параметры:**
- `user_id` (int, path) - ID пользователя

**Ответ:**
- `204 No Content` - Пользователь удален
- `404 Not Found` - Пользователь не найден

**Пример:**
```bash
curl -X DELETE http://localhost:8000/users/1
```

## Разработка

### Линтеры и форматеры

Проект использует `pre-commit` для автоматической проверки кода перед коммитом.

#### Установка pre-commit

```bash
# Установка хуков
uv run pre-commit install
```

#### Ручной запуск проверок

```bash
# Запуск всех проверок на всех файлах
uv run pre-commit run --all-files

# Форматирование кода
uv run black app

# Сортировка импортов
uv run isort app

# Проверка качества кода (без миграций)
uv run pylint app --ignore=migrations
```

#### Конфигурация

- **Black** и **isort**: настройки в `pyproject.toml`
- **Pylint**: настройки в `.pylintrc`
- **Pre-commit**: настройки в `.pre-commit-config.yaml`

Миграции Alembic исключены из проверки pylint, так как они генерируются автоматически.

### Работа с Docker

#### Сборка образа

```bash
# Сборка образа приложения
docker compose build

# Сборка с пересозданием кеша
docker compose build --no-cache
```

#### Entrypoint

При запуске контейнера используется `entrypoint.sh`, который:
1. Ожидает готовности базы данных (проверка через `netcat`)
2. Применяет миграции Alembic автоматически
3. Запускает приложение

#### Создание миграций

```bash
# В контейнере
docker compose exec app sh -c "cd app && uv run alembic revision --autogenerate -m 'описание изменений'"

# Локально
cd app
uv run alembic revision --autogenerate -m "описание изменений"
```

#### Перезапуск сервисов

```bash
# Перезапустить только приложение
docker compose restart app

# Перезапустить все сервисы
docker compose restart
```

### Доступ к базе данных

**Через PgAdmin:**
- URL: http://localhost:8081
- Email: admin@lab2.com
- Password: admin

## Структура данных

### User (Пользователь)

| Поле | Тип | Описание |
|------|-----|----------|
| id | int | Уникальный идентификатор (autoincrement) |
| username | str | Имя пользователя (уникальное) |
| email | str | Email адрес (уникальный) |
| description | str \| None | Описание пользователя (опционально) |
| created_at | datetime | Дата и время создания |
| updated_at | datetime \| None | Дата и время последнего обновления |

## Обработка ошибок

| HTTP Статус | Описание |
|-------------|----------|
| 200 OK | Успешный запрос (GET, PUT) |
| 201 Created | Ресурс создан (POST) |
| 204 No Content | Ресурс удален (DELETE) |
| 400 Bad Request | Ошибка валидации (дублирующийся email/username) |
| 404 Not Found | Ресурс не найден |
| 422 Unprocessable Entity | Невалидные данные (Pydantic валидация) |
