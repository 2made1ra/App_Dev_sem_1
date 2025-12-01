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
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import (
    OrderCreate,
    OrderUpdate,
    OrderUpdateMessage,
)
from app.schemas.product_schema import (
    ProductCreate,
    ProductUpdate,
    ProductUpdateMessage,
)
from app.services.order_service import OrderService
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


async def get_order_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OrderRepository:
    """Провайдер репозитория заказов."""
    return OrderRepository()


async def get_order_service(
    order_repository: Annotated[OrderRepository, Depends(get_order_repository)],
    product_repository: Annotated[ProductRepository, Depends(get_product_repository)],
) -> OrderService:
    """Провайдер сервиса заказов."""
    return OrderService(order_repository, product_repository)


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


# Обработчики сообщений о заказах
@broker.subscriber("order")
async def subscribe_order_create(
    order_data: OrderCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> None:
    """
    Обработчик создания заказа через RabbitMQ.

    Проверяет наличие всех товаров перед созданием заказа.
    Если хотя бы один товар закончился (stock_quantity == 0), заказ не создается.

    Args:
        order_data: Данные для создания заказа
        session: Сессия базы данных
        order_service: Сервис для работы с заказами
        product_service: Сервис для работы с продуктами
    """
    try:
        logger.info("Received order create request: User ID=%s", order_data.user_id)

        # Проверка наличия всех товаров перед созданием заказа
        out_of_stock_products = []
        for item in order_data.items:
            product = await product_service.get_by_id(session, item.product_id)
            if not product:
                logger.error(
                    "Product with ID=%s not found, order rejected", item.product_id
                )
                return
            if product.stock_quantity == 0:
                out_of_stock_products.append(
                    {"product_id": product.id, "name": product.name}
                )

        # Если есть товары, которые закончились, отклоняем заказ
        if out_of_stock_products:
            logger.warning(
                "Order rejected: products out of stock: %s", out_of_stock_products
            )
            return

        # Создаем заказ (OrderService.create уже проверяет достаточность количества)
        order = await order_service.create(session, order_data)
        logger.info(
            "Order created successfully: ID=%s, User ID=%s, Total=%s",
            order.id,
            order.user_id,
            order.total_price,
        )
    except ValueError as e:
        logger.error("Error creating order: %s", e)
    except (RuntimeError, ConnectionError) as e:
        logger.error("Unexpected error creating order: %s", e, exc_info=True)


@broker.subscriber("order_update")
async def subscribe_order_update(
    message: OrderUpdateMessage,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    order_service: Annotated[OrderService, Depends(get_order_service)],
) -> None:
    """
    Обработчик обновления статуса заказа через RabbitMQ.

    Args:
        message: Сообщение с ID заказа и данными для обновления
        session: Сессия базы данных
        order_service: Сервис для работы с заказами
    """
    try:
        logger.info("Received order update request: ID=%s", message.order_id)

        order = await order_service.update(
            session, message.order_id, message.order_data
        )
        logger.info(
            "Order updated successfully: ID=%s, Status=%s", order.id, order.status
        )
    except ValueError as e:
        logger.error("Error updating order: %s", e)
    except (RuntimeError, ConnectionError) as e:
        logger.error("Unexpected error updating order: %s", e, exc_info=True)
