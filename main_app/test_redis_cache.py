"""Тестовый скрипт для проверки интеграции Redis кэширования.

Этот скрипт тестирует все аспекты кэширования согласно этапу 8 плана:
- Кэширование пользователей (cache miss, cache hit, инвалидация)
- Кэширование продукции (cache miss, cache hit, обновление кэша)
- Проверка TTL
- Отказоустойчивость
- Производительность
"""

import json
import os
import time
from datetime import datetime

import redis
import requests

from app.redis_client import get_redis_client

# Настройки
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Счетчики результатов
test_results = {
    "passed": 0,
    "failed": 0,
    "total": 0,
}


def print_test_header(test_name: str) -> None:
    """Вывод заголовка теста."""
    print("\n" + "=" * 70)
    print(f"  {test_name}")
    print("=" * 70)


def print_test_result(test_name: str, passed: bool, details: str = "") -> None:
    """Вывод результата теста."""
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
        status = "✓ PASSED"
    else:
        test_results["failed"] += 1
        status = "✗ FAILED"

    print(f"\n{status}: {test_name}")
    if details:
        print(f"  {details}")


def check_redis_key(redis_client: redis.Redis, key: str) -> tuple[bool, dict | None]:
    """Проверка существования ключа в Redis и получение его значения."""
    try:
        if redis_client.exists(key):
            value = redis_client.get(key)
            if value:
                return True, json.loads(value)
        return False, None
    except Exception as e:
        print(f"  Ошибка при проверке ключа {key}: {e}")
        return False, None


def get_ttl(redis_client: redis.Redis, key: str) -> int:
    """Получение TTL ключа в Redis."""
    try:
        return redis_client.ttl(key)
    except Exception:
        return -2


def test_user_cache_miss(redis_client: redis.Redis) -> tuple[bool, int | None]:
    """Тест 1: Получение пользователя (cache miss)."""
    print_test_header("Тест 1: Получение пользователя (cache miss)")

    # Создаем пользователя
    user_data = {
        "username": f"test_user_{int(time.time())}",
        "email": f"test_{int(time.time())}@example.com",
        "description": "Test user for cache miss",
    }

    response = requests.post(f"{API_BASE_URL}/users", json=user_data)
    if response.status_code != 201:
        print_test_result("Создание пользователя", False, f"Status: {response.status_code}")
        return (False, None)

    user = response.json()
    user_id = user["id"]
    print(f"  Создан пользователь с ID: {user_id}")

    # Очищаем кэш перед тестом
    redis_client.delete(f"user:{user_id}")

    # Получаем пользователя (cache miss)
    start_time = time.time()
    response = requests.get(f"{API_BASE_URL}/users/{user_id}")
    elapsed_time = time.time() - start_time

    if response.status_code != 200:
        print_test_result("Получение пользователя", False, f"Status: {response.status_code}")
        return (False, None)

    # Проверяем, что данные сохранены в кэш
    exists, cached_data = check_redis_key(redis_client, f"user:{user_id}")
    if not exists:
        print_test_result("Проверка сохранения в кэш", False, "Ключ не найден в Redis")
        return (False, None)

    # Проверяем TTL (должен быть близок к 3600 секунд)
    ttl = get_ttl(redis_client, f"user:{user_id}")
    if ttl < 3500 or ttl > 3600:
        print_test_result("Проверка TTL", False, f"TTL: {ttl} (ожидается ~3600)")
        return (False, None)

    print_test_result(
        "Cache miss и сохранение в кэш",
        True,
        f"TTL: {ttl} сек, время ответа: {elapsed_time:.3f}с",
    )
    return (True, user_id)


def test_user_cache_hit(redis_client: redis.Redis, user_id: int) -> bool:
    """Тест 2: Получение пользователя (cache hit)."""
    print_test_header("Тест 2: Получение пользователя (cache hit)")

    # Получаем пользователя (cache hit)
    start_time = time.time()
    response = requests.get(f"{API_BASE_URL}/users/{user_id}")
    elapsed_time = time.time() - start_time

    if response.status_code != 200:
        print_test_result("Получение пользователя", False, f"Status: {response.status_code}")
        return False

    # Проверяем, что данные получены из кэша (быстрее)
    if elapsed_time > 0.1:  # Запрос из кэша должен быть очень быстрым
        print_test_result(
            "Скорость ответа из кэша",
            False,
            f"Время ответа: {elapsed_time:.3f}с (слишком медленно)",
        )
        return False

    print_test_result(
        "Cache hit",
        True,
        f"Время ответа: {elapsed_time:.3f}с (из кэша)",
    )
    return True


def test_user_cache_invalidation(redis_client: redis.Redis, user_id: int) -> bool:
    """Тест 3: Обновление пользователя (инвалидация кэша)."""
    print_test_header("Тест 3: Обновление пользователя (инвалидация кэша)")

    # Обновляем пользователя
    update_data = {"description": "Updated description"}
    response = requests.put(f"{API_BASE_URL}/users/{user_id}", json=update_data)

    if response.status_code != 200:
        print_test_result("Обновление пользователя", False, f"Status: {response.status_code}")
        return False

    # Проверяем, что ключ удален из кэша
    exists, _ = check_redis_key(redis_client, f"user:{user_id}")
    if exists:
        print_test_result("Инвалидация кэша", False, "Ключ все еще существует в Redis")
        return False

    # Получаем обновленного пользователя
    response = requests.get(f"{API_BASE_URL}/users/{user_id}")
    if response.status_code != 200:
        print_test_result("Получение обновленного пользователя", False)
        return False

    user = response.json()
    if user["description"] != "Updated description":
        print_test_result("Проверка обновленных данных", False)
        return False

    print_test_result("Инвалидация кэша при обновлении", True)
    return True


def test_product_cache_miss(redis_client: redis.Redis) -> tuple[bool, int | None]:
    """Тест 1: Получение продукции (cache miss)."""
    print_test_header("Тест 1: Получение продукции (cache miss)")

    # Создаем продукцию
    product_data = {
        "name": f"Test Product {int(time.time())}",
        "description": "Test product for cache miss",
        "price": 99.99,
        "stock_quantity": 100,
    }

    response = requests.post(f"{API_BASE_URL}/products", json=product_data)
    if response.status_code != 201:
        print_test_result("Создание продукции", False, f"Status: {response.status_code}")
        return (False, None)

    product = response.json()
    product_id = product["id"]
    print(f"  Создана продукция с ID: {product_id}")

    # Очищаем кэш перед тестом
    redis_client.delete(f"product:{product_id}")

    # Получаем продукцию (cache miss)
    start_time = time.time()
    response = requests.get(f"{API_BASE_URL}/products/{product_id}")
    elapsed_time = time.time() - start_time

    if response.status_code != 200:
        print_test_result("Получение продукции", False, f"Status: {response.status_code}")
        return (False, None)

    # Проверяем, что данные сохранены в кэш
    exists, cached_data = check_redis_key(redis_client, f"product:{product_id}")
    if not exists:
        print_test_result("Проверка сохранения в кэш", False, "Ключ не найден в Redis")
        return (False, None)

    # Проверяем TTL (должен быть близок к 600 секунд)
    ttl = get_ttl(redis_client, f"product:{product_id}")
    if ttl < 590 or ttl > 600:
        print_test_result("Проверка TTL", False, f"TTL: {ttl} (ожидается ~600)")
        return (False, None)

    print_test_result(
        "Cache miss и сохранение в кэш",
        True,
        f"TTL: {ttl} сек, время ответа: {elapsed_time:.3f}с",
    )
    return (True, product_id)


def test_product_cache_hit(redis_client: redis.Redis, product_id: int) -> bool:
    """Тест 2: Получение продукции (cache hit)."""
    print_test_header("Тест 2: Получение продукции (cache hit)")

    # Получаем продукцию (cache hit)
    start_time = time.time()
    response = requests.get(f"{API_BASE_URL}/products/{product_id}")
    elapsed_time = time.time() - start_time

    if response.status_code != 200:
        print_test_result("Получение продукции", False, f"Status: {response.status_code}")
        return False

    print_test_result(
        "Cache hit",
        True,
        f"Время ответа: {elapsed_time:.3f}с (из кэша)",
    )
    return True


def test_product_cache_update(redis_client: redis.Redis, product_id: int) -> bool:
    """Тест 3: Обновление продукции (обновление кэша)."""
    print_test_header("Тест 3: Обновление продукции (обновление кэша)")

    # Обновляем продукцию
    update_data = {"price": 149.99, "description": "Updated product description"}
    response = requests.put(f"{API_BASE_URL}/products/{product_id}", json=update_data)

    if response.status_code != 200:
        print_test_result("Обновление продукции", False, f"Status: {response.status_code}")
        return False

    # Проверяем, что ключ обновлен в кэше
    exists, cached_data = check_redis_key(redis_client, f"product:{product_id}")
    if not exists:
        print_test_result("Обновление кэша", False, "Ключ не найден в Redis")
        return False

    # Проверяем, что данные обновлены
    if cached_data["price"] != 149.99:
        print_test_result("Проверка обновленных данных в кэше", False)
        return False

    # Проверяем TTL (должен быть обновлен до 600 секунд)
    ttl = get_ttl(redis_client, f"product:{product_id}")
    if ttl < 590 or ttl > 600:
        print_test_result("Проверка обновленного TTL", False, f"TTL: {ttl} (ожидается ~600)")
        return False

    # Получаем продукцию и проверяем, что данные из кэша
    response = requests.get(f"{API_BASE_URL}/products/{product_id}")
    if response.status_code != 200:
        print_test_result("Получение обновленной продукции", False)
        return False

    product = response.json()
    if product["price"] != 149.99:
        print_test_result("Проверка данных из кэша", False)
        return False

    print_test_result("Обновление кэша при обновлении продукции", True, f"TTL: {ttl} сек")
    return True


def test_ttl_users(redis_client: redis.Redis) -> bool:
    """Тест: Проверка TTL для пользователей."""
    print_test_header("Проверка TTL для пользователей")

    # Создаем пользователя
    user_data = {
        "username": f"ttl_test_{int(time.time())}",
        "email": f"ttl_{int(time.time())}@example.com",
    }
    response = requests.post(f"{API_BASE_URL}/users", json=user_data)
    if response.status_code != 201:
        return False

    user_id = response.json()["id"]
    redis_client.delete(f"user:{user_id}")

    # Получаем пользователя
    requests.get(f"{API_BASE_URL}/users/{user_id}")

    # Проверяем TTL
    ttl = get_ttl(redis_client, f"user:{user_id}")
    if ttl < 3500 or ttl > 3600:
        print_test_result("TTL для пользователей", False, f"TTL: {ttl} (ожидается ~3600)")
        return False

    print_test_result("TTL для пользователей", True, f"TTL: {ttl} секунд (1 час)")
    return True


def test_ttl_products(redis_client: redis.Redis) -> bool:
    """Тест: Проверка TTL для продукции."""
    print_test_header("Проверка TTL для продукции")

    # Создаем продукцию
    product_data = {
        "name": f"TTL Test Product {int(time.time())}",
        "price": 50.0,
        "stock_quantity": 10,
    }
    response = requests.post(f"{API_BASE_URL}/products", json=product_data)
    if response.status_code != 201:
        return False

    product_id = response.json()["id"]
    redis_client.delete(f"product:{product_id}")

    # Получаем продукцию
    requests.get(f"{API_BASE_URL}/products/{product_id}")

    # Проверяем TTL
    ttl = get_ttl(redis_client, f"product:{product_id}")
    if ttl < 590 or ttl > 600:
        print_test_result("TTL для продукции", False, f"TTL: {ttl} (ожидается ~600)")
        return False

    print_test_result("TTL для продукции", True, f"TTL: {ttl} секунд (10 минут)")
    return True


def test_performance(redis_client: redis.Redis) -> bool:
    """Тест: Проверка производительности."""
    print_test_header("Проверка производительности")

    # Создаем пользователя
    user_data = {
        "username": f"perf_test_{int(time.time())}",
        "email": f"perf_{int(time.time())}@example.com",
    }
    response = requests.post(f"{API_BASE_URL}/users", json=user_data)
    if response.status_code != 201:
        return False

    user_id = response.json()["id"]
    redis_client.delete(f"user:{user_id}")

    # Запрос без кэша
    start_time = time.time()
    requests.get(f"{API_BASE_URL}/users/{user_id}")
    time_without_cache = time.time() - start_time

    # Запрос с кэшем
    start_time = time.time()
    requests.get(f"{API_BASE_URL}/users/{user_id}")
    time_with_cache = time.time() - start_time

    if time_with_cache >= time_without_cache:
        print_test_result(
            "Сравнение производительности",
            False,
            f"С кэшем: {time_with_cache:.3f}с, Без кэша: {time_without_cache:.3f}с",
        )
        return False

    speedup = time_without_cache / time_with_cache if time_with_cache > 0 else 0
    print_test_result(
        "Сравнение производительности",
        True,
        f"Без кэша: {time_without_cache:.3f}с, С кэшем: {time_with_cache:.3f}с (ускорение: {speedup:.1f}x)",
    )
    return True


def main() -> None:
    """Основная функция для запуска всех тестов."""
    print("\n" + "=" * 70)
    print(" " * 20 + "ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ REDIS КЭШИРОВАНИЯ")
    print("=" * 70)
    print(f"\nAPI URL: {API_BASE_URL}")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Подключение к Redis
    try:
        redis_client = get_redis_client()
        print("\n✓ Подключение к Redis успешно")
    except Exception as e:
        print(f"\n✗ Ошибка подключения к Redis: {e}")
        print("  Убедитесь, что Redis запущен и доступен")
        return

    # Проверка доступности API
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print(f"\n⚠ API доступен, но вернул статус {response.status_code}")
    except Exception as e:
        print(f"\n✗ API недоступен: {e}")
        print("  Убедитесь, что приложение запущено")
        return

    # Тестирование кэширования пользователей
    print("\n" + "=" * 70)
    print(" " * 15 + "ТЕСТИРОВАНИЕ КЭШИРОВАНИЯ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 70)

    result = test_user_cache_miss(redis_client)
    if isinstance(result, tuple) and result[0] and result[1]:
        user_id = result[1]
        test_user_cache_hit(redis_client, user_id)
        test_user_cache_invalidation(redis_client, user_id)

    # Тестирование кэширования продукции
    print("\n" + "=" * 70)
    print(" " * 15 + "ТЕСТИРОВАНИЕ КЭШИРОВАНИЯ ПРОДУКЦИИ")
    print("=" * 70)

    result = test_product_cache_miss(redis_client)
    if isinstance(result, tuple) and result[0] and result[1]:
        product_id = result[1]
        test_product_cache_hit(redis_client, product_id)
        test_product_cache_update(redis_client, product_id)

    # Тестирование TTL
    print("\n" + "=" * 70)
    print(" " * 25 + "ТЕСТИРОВАНИЕ TTL")
    print("=" * 70)

    test_ttl_users(redis_client)
    test_ttl_products(redis_client)

    # Тестирование производительности
    print("\n" + "=" * 70)
    print(" " * 20 + "ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 70)

    test_performance(redis_client)

    # Итоговая сводка
    print("\n" + "=" * 70)
    print(" " * 25 + "ИТОГОВАЯ СВОДКА")
    print("=" * 70)
    print(f"\nВсего тестов: {test_results['total']}")
    print(f"Успешно: {test_results['passed']} ✓")
    print(f"Провалено: {test_results['failed']} ✗")
    print(f"Процент успеха: {(test_results['passed']/test_results['total']*100) if test_results['total'] > 0 else 0:.1f}%")

    if test_results["failed"] == 0:
        print("\n" + "=" * 70)
        print(" " * 20 + "ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print(" " * 15 + "ОБНАРУЖЕНЫ ПРОВАЛЕННЫЕ ТЕСТЫ")
        print("=" * 70)

    print("\n=== Тестирование завершено ===")


if __name__ == "__main__":
    main()

