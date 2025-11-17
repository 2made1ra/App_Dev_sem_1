# Лабораторная работа 3

Веб-приложение на базе фреймворка Litestar с использованием Dependency Injection и SQLAlchemy ORM для работы с пользователями.

## Быстрый старт

```bash
# 1. Создайте .env файл (см. раздел "Установка и запуск")
# 2. Запустите всё одной командой:
docker-compose up -d

# 3. Приложение доступно по адресу:
# http://localhost:8000
# http://localhost:8000/schema/swagger (API документация)
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
```

> **Примечание:** `DATABASE_URL` для контейнера настраивается автоматически в `docker-compose.yml`.

#### 3. Запуск всех сервисов

```bash
docker-compose up -d
```

Эта команда автоматически:
- Соберёт Docker образ приложения
- Запустит PostgreSQL базу данных
- Запустит PgAdmin
- Применит миграции базы данных
- Запустит веб-приложение

#### 4. Проверка статуса

```bash
docker-compose ps
```

Все сервисы должны быть в статусе `Up`:
- `app_lab3` - веб-приложение на порту `8000`
- `db_postgres_lab2` - PostgreSQL на порту `5433`
- `pgadmin4_lab2` - PgAdmin на порту `8081`

#### 5. Просмотр логов

```bash
# Все логи
docker-compose logs -f

# Только приложение
docker-compose logs -f app

# Только база данных
docker-compose logs -f db
```

#### 6. Остановка сервисов

```bash
docker-compose down
```

Для полной очистки (включая volumes):

```bash
docker-compose down -v
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
docker-compose up -d db pgadmin
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
- **API документация (Swagger)**: http://localhost:8000/schema/swagger
- **PgAdmin**: http://localhost:8081
- **PostgreSQL**: localhost:5433

## API Документация

После запуска приложения доступна интерактивная документация:

- **Swagger UI**: http://localhost:8000/schema/swagger
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

### Работа с Docker

#### Создание миграций (в контейнере)

```bash
# Создать новую миграцию
docker-compose exec app sh -c "cd app && ../.venv/bin/alembic revision --autogenerate -m 'описание изменений'"

# Применить миграции
docker-compose exec app sh -c "cd app && ../.venv/bin/alembic upgrade head"
```

#### Создание миграций (локально)

Если вы запускаете приложение локально:

```bash
cd app
../.venv/bin/alembic revision --autogenerate -m "описание изменений"
../.venv/bin/alembic upgrade head
```

### Горячая перезагрузка (для разработки)

При использовании Docker, изменения в коде автоматически подхватываются благодаря volume mounts. Однако для применения изменений в зависимостях или перезапуска приложения:

```bash
# Перезапустить только приложение
docker-compose restart app

# Перезапустить все сервисы
docker-compose restart
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
