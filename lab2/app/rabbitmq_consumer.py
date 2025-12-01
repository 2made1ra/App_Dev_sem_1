"""Модуль для обработки сообщений из RabbitMQ."""

import logging
import os
from typing import Annotated

from faststream import Depends, FastStream
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.dependencies import (
    provide_order_repository,
    provide_order_service,
    provide_product_repository,
    provide_product_service,
)
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate, OrderUpdate
from app.schemas.product_schema import (
    ProductCreate,
    ProductUpdate,
    ProductUpdateMessage,
)
from app.services.product_service import ProductService

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


# Инициализация брокера и приложения
rabbitmq_url = get_rabbitmq_url()
logger.info("Connecting to RabbitMQ: %s", rabbitmq_url)

broker = RabbitBroker(rabbitmq_url)
app = FastStream(broker)


# Провайдеры для dependency injection
async def get_db_session() -> AsyncSession:
    """Провайдер сессии базы данных для RabbitMQ consumer."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_product_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductRepository:
    """Провайдер репозитория продуктов."""
    return ProductRepository()


async def get_product_service(
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ProductService:
    """Провайдер сервиса продуктов."""
    return ProductService(product_repository)


# Обработчики сообщений о продукции
@broker.subscriber("product")
async def subscribe_product_create(
    product_data: ProductCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> None:
    """
    Обработчик создания продукта через RabbitMQ.

    Args:
        product_data: Данные для создания продукта
        session: Сессия базы данных
        product_service: Сервис для работы с продуктами
    """
    try:
        logger.info("Received product create request: %s", product_data.name)
        product = await product_service.create(session, product_data)
        logger.info(
            "Product created successfully: ID=%s, Name=%s", product.id, product.name
        )
    except ValueError as e:
        logger.error("Error creating product: %s", e)
    except (RuntimeError, ConnectionError) as e:
        logger.error("Unexpected error creating product: %s", e, exc_info=True)


@broker.subscriber("product_update")
async def subscribe_product_update(
    message: ProductUpdateMessage,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> None:
    """
    Обработчик обновления продукта через RabbitMQ.

    Args:
        message: Сообщение с ID продукта и данными для обновления
        session: Сессия базы данных
        product_service: Сервис для работы с продуктами
    """
    try:
        logger.info("Received product update request: ID=%s", message.product_id)

        product = await product_service.update(
            session, message.product_id, message.product_data
        )
        logger.info(
            "Product updated successfully: ID=%s, Stock=%s",
            product.id,
            product.stock_quantity,
        )

        # Проверка, не закончился ли товар на складе
        if product.stock_quantity == 0:
            logger.warning(
                "Product %s (ID=%s) is out of stock!", product.name, product.id
            )
    except ValueError as e:
        logger.error("Error updating product: %s", e)
    except (RuntimeError, ConnectionError) as e:
        logger.error("Unexpected error updating product: %s", e, exc_info=True)
