"""Модуль для управления кэшем продукции в Redis."""

import json
import logging

import redis

logger = logging.getLogger(__name__)


def get_product_from_cache(redis_client: redis.Redis, product_id: int) -> dict | None:
    """
    Получение данных продукции из кэша Redis.

    Args:
        redis_client: Клиент Redis для выполнения операций
        product_id: Идентификатор продукции

    Returns:
        dict | None: Словарь с данными продукции, если найден в кэше,
                     иначе None
    """
    key = f"product:{product_id}"

    try:
        cached_data = redis_client.get(key)
        if cached_data is None:
            logger.debug("Cache miss для продукции: product_id=%s", product_id)
            return None

        product_data = json.loads(cached_data)
        logger.info("Cache hit для продукции: product_id=%s", product_id)
        return product_data

    except redis.ConnectionError as e:
        logger.warning(
            "Ошибка подключения к Redis при получении продукции из кэша: %s",
            e,
        )
        return None
    except json.JSONDecodeError as e:
        logger.error(
            "Ошибка десериализации данных продукции из кэша: product_id=%s, error=%s",
            product_id,
            e,
        )
        # Удаляем поврежденные данные из кэша
        try:
            redis_client.delete(key)
        except redis.ConnectionError:
            pass
        return None


def set_product_to_cache(
    redis_client: redis.Redis,
    product_id: int,
    product_data: dict,
    ttl: int = 600,
) -> None:
    """
    Сохранение данных продукции в кэш Redis с TTL.

    Args:
        redis_client: Клиент Redis для выполнения операций
        product_id: Идентификатор продукции
        product_data: Словарь с данными продукции для сохранения
        ttl: Время жизни ключа в секундах (по умолчанию 10 минут = 600 секунд)
    """
    key = f"product:{product_id}"

    try:
        json_data = json.dumps(product_data)
        redis_client.setex(key, ttl, json_data)
        logger.info(
            "Данные продукции сохранены в кэш: product_id=%s, ttl=%s секунд",
            product_id,
            ttl,
        )
    except redis.ConnectionError as e:
        logger.warning(
            "Ошибка подключения к Redis при сохранении продукции в кэш: %s",
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику
    except (TypeError, ValueError) as e:
        logger.error(
            "Ошибка сериализации данных продукции для кэша: product_id=%s, error=%s",
            product_id,
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику


def update_product_in_cache(
    redis_client: redis.Redis,
    product_id: int,
    product_data: dict,
    ttl: int = 600,
) -> None:
    """
    Обновление данных продукции в кэше Redis с TTL.

    При обновлении продукции данные обновляются в кэше (в отличие от пользователей,
    где происходит инвалидация). Это обеспечивает актуальность данных без
    необходимости повторного запроса к БД.

    Args:
        redis_client: Клиент Redis для выполнения операций
        product_id: Идентификатор продукции
        product_data: Словарь с обновленными данными продукции
        ttl: Время жизни ключа в секундах (по умолчанию 10 минут = 600 секунд)
    """
    key = f"product:{product_id}"

    try:
        json_data = json.dumps(product_data)
        # setex работает как set, если ключа нет - он будет создан
        redis_client.setex(key, ttl, json_data)
        logger.info(
            "Данные продукции обновлены в кэше: product_id=%s, ttl=%s секунд",
            product_id,
            ttl,
        )
    except redis.ConnectionError as e:
        logger.warning(
            "Ошибка подключения к Redis при обновлении продукции в кэше: %s",
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику
    except (TypeError, ValueError) as e:
        logger.error(
            "Ошибка сериализации данных продукции для обновления кэша: product_id=%s, error=%s",
            product_id,
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику


def delete_product_from_cache(redis_client: redis.Redis, product_id: int) -> None:
    """
    Удаление данных продукции из кэша Redis.

    Args:
        redis_client: Клиент Redis для выполнения операций
        product_id: Идентификатор продукции
    """
    key = f"product:{product_id}"

    try:
        deleted = redis_client.delete(key)
        if deleted:
            logger.info("Данные продукции удалены из кэша: product_id=%s", product_id)
        else:
            logger.debug("Ключ продукции не найден в кэше: product_id=%s", product_id)
    except redis.ConnectionError as e:
        logger.warning(
            "Ошибка подключения к Redis при удалении продукции из кэша: %s",
            e,
        )
        # Не выбрасываем исключение, чтобы не блокировать основную логику
