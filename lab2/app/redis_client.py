"""Модуль для работы с Redis клиентом."""

import logging
import os

import redis

logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    """
    Создание и возврат клиента Redis.

    Получает параметры подключения из переменных окружения:
    - REDIS_HOST (по умолчанию localhost)
    - REDIS_PORT (по умолчанию 6379)
    - REDIS_DB (по умолчанию 0)
    - REDIS_DECODE_RESPONSES (по умолчанию True)

    Returns:
        redis.Redis: Экземпляр клиента Redis

    Raises:
        redis.ConnectionError: Если не удалось подключиться к Redis
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    decode_responses = os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true"

    redis_client = redis.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=decode_responses,
    )

    # Проверка подключения
    try:
        redis_client.ping()
        logger.info(
            "Успешное подключение к Redis: host=%s, port=%s, db=%s",
            host,
            port,
            db,
        )
    except redis.ConnectionError as e:
        logger.error("Ошибка подключения к Redis: %s", e)
        raise

    return redis_client


def ping_redis(redis_client: redis.Redis) -> bool:
    """
    Проверка доступности Redis.

    Args:
        redis_client: Клиент Redis для проверки

    Returns:
        bool: True при успешном подключении, False при ошибке
    """
    try:
        redis_client.ping()
        logger.info("Проверка подключения к Redis: успешно")
        return True
    except redis.ConnectionError as e:
        logger.warning("Ошибка проверки подключения к Redis: %s", e)
        return False
