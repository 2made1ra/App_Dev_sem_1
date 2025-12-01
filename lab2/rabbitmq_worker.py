"""Скрипт для запуска RabbitMQ consumer в отдельном процессе."""

import asyncio
import logging

from app.rabbitmq_consumer import app

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция для запуска RabbitMQ consumer."""
    logger.info("Starting RabbitMQ worker...")
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("RabbitMQ worker stopped by user")
    except Exception as e:
        logger.error("Error running RabbitMQ worker: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

