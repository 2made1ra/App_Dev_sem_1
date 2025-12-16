# Курсовой проект "Разработка приложений" магистратуры "Прикладной анализ данных"

Веб-приложение на базе фреймворка Litestar с использованием Dependency Injection, SQLAlchemy ORM, RabbitMQ для асинхронной обработки сообщений, Redis для кэширования данных о пользователях, продуктах и заказах, и TaskIQ для планирования и выполнения периодических задач.

## Описание

E-Commerce приложение для управления пользователями, продуктами и заказами с поддержкой:
- RESTful API на базе Litestar
- Асинхронная обработка через RabbitMQ
- Кэширование данных в Redis
- Планирование задач через TaskIQ
- Автоматические миграции базы данных через Alembic

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd main_app
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=lab_db2

PGADMIN_DEFAULT_EMAIL=admin@main_app.com
PGADMIN_DEFAULT_PASSWORD=admin

DB_HOST=db
DB_PORT=5432
HOST=0.0.0.0
PORT=8000

# RabbitMQ настройки
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_VHOST=local
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Redis настройки
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_DECODE_RESPONSES=true
```

### 3. Запуск через Docker Compose

```bash
# Сборка и запуск всех сервисов
docker compose up --build

# Или в фоновом режиме
docker compose up --build -d
```

Эта команда автоматически:
- Соберёт Docker образ приложения
- Запустит PostgreSQL базу данных
- Запустит PgAdmin
- Запустит RabbitMQ брокер сообщений
- Запустит Redis для кэширования
- Применит миграции базы данных
- Запустит веб-приложение (REST API)
- Запустит RabbitMQ worker для обработки сообщений
- Запустит TaskIQ scheduler и worker для планирования задач

### 4. Проверка статуса

```bash
docker compose ps
```

### 5. Доступ к сервисам

После запуска приложение и сервисы будут доступны по следующим адресам:

- **Веб-приложение**: http://localhost:8000
- **API документация (Swagger)**: http://localhost:8000/docs
- **PgAdmin**: http://localhost:8081
- **PostgreSQL**: localhost:5433
- **RabbitMQ Management UI**: http://localhost:15672 (логин: `guest`, пароль: `guest`)
- **RabbitMQ AMQP**: localhost:5672
- **Redis**: localhost:6379

### 6. Остановка сервисов

```bash
# Остановка
docker compose down

# Остановка с удалением volumes
docker compose down -v
```

## Основные фишки

### 1. Dependency Injection (DI)
- Все зависимости инжектируются через Litestar DI контейнер
- Чистая архитектура с разделением на слои: Controllers → Services → Repositories

### 2. Кэширование в Redis
- **Cache-Aside** стратегия для пользователей и продукции
- TTL: пользователи - 1 час, продукция - 10 минут
- Автоматическая инвалидация кэша при обновлении данных

### 3. Асинхронная обработка через RabbitMQ
- Создание и обновление продуктов/заказов через очереди
- Отдельный worker для обработки сообщений
- Очереди: `product`, `product_update`, `order`, `order_update`, `report`

### 4. Планировщик задач TaskIQ
- Автоматическая генерация отчетов по заказам каждый день в полночь
- Распределенная система очередей задач
- Поддержка cron-выражений для расписания

### 5. Миграции базы данных
- Автоматическое применение миграций при запуске через `entrypoint.sh`
- Alembic для управления схемой БД

## Тестирование

### Запуск unit-тестов

```bash
# Запуск всех тестов
uv run pytest

# С покрытием кода
uv run pytest --cov=app --cov-report=html

# Запуск конкретного теста
uv run pytest tests/test_controllers/test_user_controller.py

# Запуск с подробным выводом
uv run pytest -v
```

### Тестирование кэширования Redis

```bash
# Запуск тестов кэширования
uv run python test_redis_cache.py
```

### Тестирование API эндпоинтов

```bash
# Запуск bash-скрипта для тестирования API
bash test_report_api.sh
```

## Архитектура

### Структура проекта

```
main_app/
├── app/
│   ├── controllers/      # HTTP контроллеры (REST API endpoints)
│   ├── services/         # Бизнес-логика
│   ├── repositories/     # Работа с базой данных
│   ├── schemas/          # Pydantic схемы для валидации
│   ├── models.py         # SQLAlchemy модели
│   ├── cache/            # Модули кэширования (Redis)
│   ├── dependencies.py   # DI провайдеры
│   ├── scheduler.py      # TaskIQ планировщик задач
│   └── rabbitmq_consumer.py  # RabbitMQ consumer
├── tests/                # Unit-тесты
├── main.py               # Точка входа приложения
├── docker-compose.yml    # Docker Compose конфигурация
└── pyproject.toml        # Зависимости проекта
```

### Слои архитектуры

1. **Controllers** (`app/controllers/`)
   - Обработка HTTP запросов
   - Валидация входных данных через Pydantic схемы
   - Возврат HTTP ответов

2. **Services** (`app/services/`)
   - Бизнес-логика приложения
   - Работа с кэшем (Redis)
   - Обработка ошибок

3. **Repositories** (`app/repositories/`)
   - Абстракция доступа к базе данных
   - SQLAlchemy запросы
   - CRUD операции

4. **Models** (`app/models.py`)
   - SQLAlchemy ORM модели
   - Определение структуры БД

5. **Cache** (`app/cache/`)
   - Модули для работы с Redis
   - Стратегии кэширования (Cache-Aside)

### Поток данных

```
HTTP Request → Controller → Service → Repository → Database
                                    ↓
                                  Cache (Redis)
```

### Асинхронная обработка

```
Producer → RabbitMQ Queue → RabbitMQ Worker → Service → Repository → Database
```

### Планировщик задач

```
TaskIQ Scheduler → Task Queue → TaskIQ Worker → Service → Repository → Database
                                                      ↓
                                                 RabbitMQ
```

## Технологический стек

- **Framework**: Litestar 2.18+
- **ORM**: SQLAlchemy 2.0+ (async)
- **Database**: PostgreSQL 17
- **Cache**: Redis 7
- **Message Broker**: RabbitMQ 3
- **Task Scheduler**: TaskIQ 0.11+
- **Migrations**: Alembic
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Code Quality**: black, isort, pylint, pre-commit
