"""Скрипт для отправки тестовых сообщений в RabbitMQ."""

import json
import logging
import os
import sys

import pika

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_rabbitmq_connection() -> pika.BlockingConnection:
    """
    Создать подключение к RabbitMQ.

    Returns:
        pika.BlockingConnection: Подключение к RabbitMQ

    Raises:
        pika.exceptions.AMQPConnectionError: Если не удалось подключиться
    """
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    vhost = os.getenv("RABBITMQ_VHOST", "local")
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")

    # Убираем начальный слэш из vhost, если он есть
    vhost = vhost.lstrip("/")

    credentials = pika.PlainCredentials(user, password)
    parameters = pika.ConnectionParameters(
        host=host, port=port, virtual_host=vhost, credentials=credentials
    )

    try:
        connection = pika.BlockingConnection(parameters)
        logger.info("Connected to RabbitMQ: %s:%s/%s", host, port, vhost)
        return connection
    except pika.exceptions.AMQPConnectionError as e:
        logger.error("Failed to connect to RabbitMQ: %s", e)
        raise


def send_message(
    connection: pika.BlockingConnection, queue_name: str, message: dict
) -> None:
    """
    Отправить сообщение в очередь RabbitMQ.

    Args:
        connection: Подключение к RabbitMQ
        queue_name: Имя очереди
        message: Сообщение для отправки (будет сериализовано в JSON)
    """
    channel = connection.channel()

    # Не объявляем очередь - она уже создана consumer'ом через FastStream
    # Если очередь не существует, RabbitMQ создаст её автоматически при отправке

    # Отправляем сообщение
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),  # Сохранять сообщения на диск
    )

    logger.info("Message sent to queue '%s': %s", queue_name, message)


def create_test_products(connection: pika.BlockingConnection) -> list[dict]:
    """
    Создать 5 тестовых продуктов и отправить их в очередь.

    Args:
        connection: Подключение к RabbitMQ

    Returns:
        list[dict]: Список созданных продуктов с их данными
    """
    products = [
        {
            "name": "Laptop Dell XPS 15",
            "description": "High-performance laptop with 16GB RAM and 512GB SSD",
            "price": 1299.99,
            "stock_quantity": 10,
        },
        {
            "name": "Wireless Mouse Logitech MX Master 3",
            "description": "Ergonomic wireless mouse with advanced tracking",
            "price": 99.99,
            "stock_quantity": 25,
        },
        {
            "name": "Mechanical Keyboard Keychron K8",
            "description": "Wireless mechanical keyboard with RGB backlight",
            "price": 89.99,
            "stock_quantity": 15,
        },
        {
            "name": "USB-C Hub 7-in-1",
            "description": "Multi-port USB-C hub with HDMI, USB 3.0, and SD card reader",
            "price": 49.99,
            "stock_quantity": 30,
        },
        {
            "name": "External SSD Samsung T7 1TB",
            "description": "Fast portable SSD with USB 3.2 Gen 2",
            "price": 149.99,
            "stock_quantity": 20,
        },
    ]

    logger.info("Creating %d products...", len(products))
    for product in products:
        send_message(connection, "product", product)
        logger.info("Product created: %s", product["name"])

    return products


def create_test_orders(connection: pika.BlockingConnection) -> list[dict]:
    """
    Создать 3 тестовых заказа и отправить их в очередь.

    Внимание: Для создания заказов требуются существующие user_id и delivery_address_id.
    По умолчанию используются user_id=1 и delivery_address_id=1.
    Убедитесь, что эти записи существуют в базе данных.

    Args:
        connection: Подключение к RabbitMQ

    Returns:
        list[dict]: Список созданных заказов с их данными
    """
    # Получаем user_id и delivery_address_id из переменных окружения или используем значения по умолчанию
    user_id = int(os.getenv("TEST_USER_ID", "1"))
    delivery_address_id = int(os.getenv("TEST_DELIVERY_ADDRESS_ID", "1"))

    orders = [
        {
            "user_id": user_id,
            "delivery_address_id": delivery_address_id,
            "items": [
                {"product_id": 1, "quantity": 1},  # Laptop
                {"product_id": 2, "quantity": 1},  # Mouse
            ],
            "status": "pending",
        },
        {
            "user_id": user_id,
            "delivery_address_id": delivery_address_id,
            "items": [
                {"product_id": 3, "quantity": 2},  # Keyboard x2
                {"product_id": 4, "quantity": 1},  # USB-C Hub
            ],
            "status": "pending",
        },
        {
            "user_id": user_id,
            "delivery_address_id": delivery_address_id,
            "items": [
                {"product_id": 5, "quantity": 1},  # External SSD
                {"product_id": 2, "quantity": 1},  # Mouse
                {"product_id": 4, "quantity": 2},  # USB-C Hub x2
            ],
            "status": "pending",
        },
    ]

    logger.info("Creating %d orders...", len(orders))
    logger.info(
        "Using user_id=%s, delivery_address_id=%s", user_id, delivery_address_id
    )
    logger.warning(
        "Make sure user_id=%s and delivery_address_id=%s exist in the database!",
        user_id,
        delivery_address_id,
    )

    for i, order in enumerate(orders, 1):
        send_message(connection, "order", order)
        logger.info("Order %d created with %d items", i, len(order["items"]))

    return orders


def main() -> None:
    """Главная функция для создания тестовых данных."""
    connection = None
    try:
        # Подключение к RabbitMQ
        connection = get_rabbitmq_connection()

        # Создание продуктов
        logger.info("=" * 50)
        logger.info("Creating test products...")
        logger.info("=" * 50)
        products = create_test_products(connection)
        logger.info("Successfully created %d products", len(products))

        # Небольшая задержка перед созданием заказов
        import time

        logger.info("Waiting 2 seconds before creating orders...")
        time.sleep(2)

        # Создание заказов
        logger.info("=" * 50)
        logger.info("Creating test orders...")
        logger.info("=" * 50)
        orders = create_test_orders(connection)
        logger.info("Successfully created %d orders", len(orders))

        logger.info("=" * 50)
        logger.info("All test data sent successfully!")
        logger.info("=" * 50)

    except pika.exceptions.AMQPConnectionError as e:
        logger.error("Failed to connect to RabbitMQ: %s", e)
        logger.error("Make sure RabbitMQ is running and accessible")
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        if connection and not connection.is_closed:
            connection.close()
            logger.info("Connection to RabbitMQ closed")


if __name__ == "__main__":
    main()

