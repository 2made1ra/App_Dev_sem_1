"""Модуль для настройки планировщика задач TaskIQ."""

import json
import logging
import os
from datetime import date, datetime

import aio_pika
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisScheduleSource

from app.database import async_session_factory
from app.repositories.order_repository import OrderRepository
from app.repositories.report_repository import ReportRepository
from app.services.report_service import ReportService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_rabbitmq_url() -> str:
    """
    Получить URL подключения к RabbitMQ из переменных окружения.

    Returns:
        str: URL для подключения к RabbitMQ в формате amqp://user:password@host:port/vhost
    """
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = os.getenv("RABBITMQ_PORT", "5672")
    vhost = os.getenv("RABBITMQ_VHOST", "local")
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")

    # Убираем начальный слэш из vhost, если он есть
    vhost = vhost.lstrip("/")

    return f"amqp://{user}:{password}@{host}:{port}/{vhost}"


def get_redis_url() -> str:
    """
    Получить URL подключения к Redis из переменных окружения.

    Returns:
        str: URL для подключения к Redis в формате redis://host:port/db
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))

    return f"redis://{host}:{port}/{db}"


# Инициализация брокера TaskIQ
rabbitmq_url = get_rabbitmq_url()
logger.info("Initializing TaskIQ broker with RabbitMQ: %s", rabbitmq_url)

broker = AioPikaBroker(rabbitmq_url)

# Инициализация источников расписаний
redis_url = get_redis_url()
logger.info("Initializing Redis schedule source: %s", redis_url)

# RedisScheduleSource для динамических расписаний
redis_schedule_source = RedisScheduleSource(redis_url)

# LabelScheduleSource для статических расписаний из декораторов задач
label_schedule_source = LabelScheduleSource(broker)

# Создание планировщика с обоими источниками расписаний
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[redis_schedule_source, label_schedule_source],
)


# Провайдеры для TaskIQ
async def provide_db_session_for_taskiq() -> AsyncSession:
    """
    Провайдер сессии базы данных для задач TaskIQ.

    Yields:
        AsyncSession: Асинхронная сессия базы данных
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def provide_order_repository_for_taskiq(
    db_session: AsyncSession = TaskiqDepends(provide_db_session_for_taskiq),
) -> OrderRepository:
    """
    Провайдер репозитория заказов для задач TaskIQ.

    Args:
        db_session: Сессия базы данных (внедряется через DI)

    Returns:
        OrderRepository: Экземпляр репозитория заказов
    """
    return OrderRepository()


async def provide_report_repository_for_taskiq(
    db_session: AsyncSession = TaskiqDepends(provide_db_session_for_taskiq),
) -> ReportRepository:
    """
    Провайдер репозитория отчетов для задач TaskIQ.

    Args:
        db_session: Сессия базы данных (внедряется через DI)

    Returns:
        ReportRepository: Экземпляр репозитория отчетов
    """
    return ReportRepository()


async def provide_report_service_for_taskiq(
    order_repository: OrderRepository = TaskiqDepends(
        provide_order_repository_for_taskiq
    ),
    report_repository: ReportRepository = TaskiqDepends(
        provide_report_repository_for_taskiq
    ),
) -> ReportService:
    """
    Провайдер сервиса отчетов для задач TaskIQ.

    Args:
        order_repository: Репозиторий заказов (внедряется через DI)
        report_repository: Репозиторий отчетов (внедряется через DI)

    Returns:
        ReportService: Экземпляр сервиса отчетов
    """
    return ReportService(order_repository, report_repository)


# Задача для формирования отчета
@broker.task(
    schedule=[
        {
            "cron": "0 0 * * *",  # Каждый день в полночь - возвращаем обратно после тестов
            "cron_offset": None,
            "args": [],
            "kwargs": {},
        }
    ]
)
async def my_scheduled_task(
    report_date: date | None = None,
    db_session: AsyncSession = TaskiqDepends(provide_db_session_for_taskiq),
    report_service: ReportService = TaskiqDepends(provide_report_service_for_taskiq),
) -> None:
    """
    Задача для формирования отчета по заказам.

    Использует ReportService для формирования отчетов за указанную дату
    и отправляет сообщение в RabbitMQ с информацией о созданных отчетах.

    Args:
        report_date: Дата для формирования отчета (по умолчанию текущая дата)
        db_session: Сессия базы данных (внедряется через DI)
        report_service: Сервис для работы с отчетами (внедряется через DI)
    """
    if report_date is None:
        report_date = date.today()

    logger.info("Starting report generation for date: %s", report_date)

    try:
        # Используем сервис для формирования отчетов
        reports = await report_service.generate_report(db_session, report_date)

        logger.info("Created %d reports for date %s", len(reports), report_date)

        # Подготавливаем данные для отправки в RabbitMQ
        reports_data = [
            {
                "report_id": report.id,
                "order_id": report.order_id,
                "count_product": report.count_product,
                "report_at": report.report_at.isoformat(),
            }
            for report in reports
        ]

        # Отправляем сообщение в RabbitMQ
        connection = await aio_pika.connect_robust(rabbitmq_url)
        try:
            channel = await connection.channel()

            message_body = {
                "report_date": report_date.isoformat(),
                "reports_count": len(reports_data),
                "reports": reports_data,
                "created_at": datetime.now().isoformat(),
            }

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message_body).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key="report",
            )

            logger.info(
                "Sent report message to RabbitMQ queue 'report' for date %s",
                report_date,
            )
        finally:
            await connection.close()
    except Exception as e:
        logger.error(
            "Error generating reports for date %s: %s", report_date, e, exc_info=True
        )
        raise


# Экспорт для использования в CLI
# Объект scheduler используется командой: taskiq scheduler app.scheduler:scheduler
# Все задачи зарегистрированы в брокере через декоратор @broker.task
