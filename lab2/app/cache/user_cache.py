"""Модуль для управления кэшем пользователей в Redis."""

import json
import logging

import redis

logger = logging.getLogger(__name__)


def get_user_from_cache(redis_client: redis.Redis, user_id: int) -> dict | None:
    """
    Получение данных пользователя из кэша Redis.

    Args:
        redis_client: Клиент Redis для выполнения операций
        user_id: Идентификатор пользователя

    Returns:
        dict | None: Словарь с данными пользователя, если найден в кэше,
                     иначе None
    """
    key = f"user:{user_id}"

    try:
        cached_data = redis_client.get(key)
        if cached_data is None:
            logger.debug("Cache miss для пользователя: user_id=%s", user_id)
            return None

        user_data = json.loads(cached_data)
        logger.info("Cache hit для пользователя: user_id=%s", user_id)
        return user_data

    except redis.ConnectionError as e:
        logger.warning(
            "Ошибка подключения к Redis при получении пользователя из кэша: %s",
            e,
        )
        return None
    except json.JSONDecodeError as e:
        logger.error(
            "Ошибка десериализации данных пользователя из кэша: user_id=%s, error=%s",
            user_id,
            e,
        )
        # Удаляем поврежденные данные из кэша
        try:
            redis_client.delete(key)
        except redis.ConnectionError:
            pass
        return None


def set_user_to_cache(
    redis_client: redis.Redis,
    user_id: int,
    user_data: dict,
    ttl: int = 3600,
) -> None:
    """
    Сохранение данных пользователя в кэш Redis с TTL.

    Args:
        redis_client: Клиент Redis для выполнения операций
        user_id: Идентификатор пользователя
        user_data: Словарь с данными пользователя для сохранения
        ttl: Время жизни ключа в секундах (по умолчанию 1 час = 3600 секунд)
    """
    key = f"user:{user_id}"

    try:
        json_data = json.dumps(user_data)
        redis_client.setex(key, ttl, json_data)
        logger.info(
            "Данные пользователя сохранены в кэш: user_id=%s, ttl=%s секунд",
            user_id,
            ttl,
        )
    except redis.ConnectionError as e:
        logger.warning(
            "Ошибка подключения к Redis при сохранении пользователя в кэш: %s",
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику
    except (TypeError, ValueError) as e:
        logger.error(
            "Ошибка сериализации данных пользователя для кэша: user_id=%s, error=%s",
            user_id,
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику


def delete_user_from_cache(redis_client: redis.Redis, user_id: int) -> None:
    """
    Удаление данных пользователя из кэша Redis.

    Args:
        redis_client: Клиент Redis для выполнения операций
        user_id: Идентификатор пользователя
    """
    key = f"user:{user_id}"

    try:
        deleted = redis_client.delete(key)
        if deleted:
            logger.info("Данные пользователя удалены из кэша: user_id=%s", user_id)
        else:
            logger.debug("Ключ пользователя не найден в кэше: user_id=%s", user_id)
    except redis.ConnectionError as e:
        logger.warning(
            "Ошибка подключения к Redis при удалении пользователя из кэша: %s",
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику
