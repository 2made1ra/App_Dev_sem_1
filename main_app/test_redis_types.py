"""Тестовый скрипт для изучения основных структур данных Redis.

Этот скрипт демонстрирует работу с различными типами данных Redis:
- Strings (строки)
- Lists (списки)
- Sets (множества)
- Hashes (хэши)
- Sorted Sets (упорядоченные множества)
- TTL (Time To Live)

Примечание: После изучения типов данных и проверки работы скрипт можно удалить
или оставить для справки.
"""

import json

import redis

from app.redis_client import get_redis_client


def test_strings(client: redis.Redis) -> None:
    """Тестирование работы со строками (Strings) в Redis."""
    print("\n=== Тестирование Strings (строки) ===")

    # Установка и получение значения
    print("\n1. Установка и получение значения:")
    client.set("user:name", "Иван")
    name = client.get("user:name")
    print(f"   Установлено: user:name = 'Иван'")
    print(f"   Получено: {name}")
    # При decode_responses=True не нужен decode('utf-8')

    # Установка значения с TTL (Time To Live)
    print("\n2. Установка значения с TTL (1 час = 3600 секунд):")
    client.setex("session:123", 3600, "active")
    ttl = client.ttl("session:123")
    print(f"   Установлено: session:123 = 'active' с TTL 3600 секунд")
    print(f"   Оставшееся время жизни: {ttl} секунд")

    # Проверка существования ключа
    print("\n3. Проверка существования ключа:")
    exists = client.exists("user:name")
    print(f"   Ключ 'user:name' существует: {exists}")

    # Работа с числами - счетчик
    print("\n4. Работа с числами (счетчик):")
    client.set("counter", 0)
    print(f"   Начальное значение счетчика: {client.get('counter')}")

    # Увеличение на 1
    client.incr("counter")
    print(f"   После incr (увеличить на 1): {client.get('counter')}")

    # Увеличение на указанное значение
    client.incrby("counter", 5)
    print(f"   После incrby('counter', 5) (увеличить на 5): {client.get('counter')}")

    # Уменьшение на 1
    client.decr("counter")
    print(f"   После decr (уменьшить на 1): {client.get('counter')}")

    # Удаление ключа
    print("\n5. Удаление ключа:")
    client.delete("user:name")
    exists_after_delete = client.exists("user:name")
    print(f"   Ключ 'user:name' после удаления существует: {exists_after_delete}")

    # Очистка тестовых ключей
    client.delete("session:123", "counter")
    print("\n   Тестовые ключи очищены")


def test_lists(client: redis.Redis) -> None:
    """Тестирование работы со списками (Lists) в Redis."""
    print("\n=== Тестирование Lists (списки) ===")

    # Добавление элементов в начало списка (lpush - left push)
    print("\n1. Добавление элементов в начало списка (lpush):")
    client.lpush("tasks", "task1", "task2")
    print("   Выполнено: lpush('tasks', 'task1', 'task2')")
    print("   lpush добавляет элементы в начало списка (слева)")
    tasks = client.lrange("tasks", 0, -1)
    print(f"   Текущее состояние списка: {tasks}")

    # Добавление элементов в конец списка (rpush - right push)
    print("\n2. Добавление элементов в конец списка (rpush):")
    client.rpush("tasks", "task3", "task4")
    print("   Выполнено: rpush('tasks', 'task3', 'task4')")
    print("   rpush добавляет элементы в конец списка (справа)")
    tasks = client.lrange("tasks", 0, -1)
    print(f"   Текущее состояние списка: {tasks}")

    # Получение всех элементов списка
    print("\n3. Получение всех элементов списка:")
    all_tasks = client.lrange("tasks", 0, -1)
    print(f"   lrange('tasks', 0, -1): {all_tasks}")
    print("   Параметры: 0 - начало списка, -1 - конец списка")

    # Получение длины списка
    print("\n4. Получение длины списка:")
    length = client.llen("tasks")
    print(f"   llen('tasks'): {length} элементов")

    # Удаление и возврат первого элемента (слева)
    print("\n5. Удаление и возврат первого элемента (lpop):")
    first_task = client.lpop("tasks")
    print(f"   lpop('tasks'): удален и возвращен элемент '{first_task}'")
    print("   lpop удаляет элемент с начала списка (слева)")
    tasks = client.lrange("tasks", 0, -1)
    print(f"   Текущее состояние списка: {tasks}")

    # Удаление и возврат последнего элемента (справа)
    print("\n6. Удаление и возврат последнего элемента (rpop):")
    last_task = client.rpop("tasks")
    print(f"   rpop('tasks'): удален и возвращен элемент '{last_task}'")
    print("   rpop удаляет элемент с конца списка (справа)")
    tasks = client.lrange("tasks", 0, -1)
    print(f"   Текущее состояние списка: {tasks}")

    # Очистка тестовых ключей
    client.delete("tasks")
    print("\n   Тестовые ключи очищены")


def test_sets(client: redis.Redis) -> None:
    """Тестирование работы с множествами (Sets) в Redis."""
    print("\n=== Тестирование Sets (множества) ===")

    # Добавление элементов в множество
    print("\n1. Добавление элементов в множество:")
    client.sadd("tags", "python", "redis", "database")
    print("   Выполнено: sadd('tags', 'python', 'redis', 'database')")
    print("   Множества хранят уникальные элементы (без дубликатов)")

    client.sadd("languages", "python", "java", "javascript")
    print("   Выполнено: sadd('languages', 'python', 'java', 'javascript')")

    # Получение всех элементов множества
    print("\n2. Получение всех элементов множества:")
    all_tags = client.smembers("tags")
    print(f"   smembers('tags'): {all_tags}")

    # Проверка принадлежности элемента
    print("\n3. Проверка принадлежности элемента:")
    is_member = client.sismember("tags", "python")
    print(f"   sismember('tags', 'python'): {is_member}")
    print("   Возвращает True, если элемент принадлежит множеству, иначе False")

    is_not_member = client.sismember("tags", "ruby")
    print(f"   sismember('tags', 'ruby'): {is_not_member}")

    # Получение количества элементов
    print("\n4. Получение количества элементов:")
    count = client.scard("tags")
    print(f"   scard('tags'): {count} элементов")

    # Операции с множествами - пересечение
    print("\n5. Операции с множествами:")
    intersection = client.sinter("tags", "languages")
    print(f"   sinter('tags', 'languages') - пересечение: {intersection}")
    print("   Пересечение возвращает элементы, присутствующие в обоих множествах")

    # Объединение множеств
    union = client.sunion("tags", "languages")
    print(f"   sunion('tags', 'languages') - объединение: {union}")
    print("   Объединение возвращает все уникальные элементы из обоих множеств")

    # Разность множеств
    difference = client.sdiff("tags", "languages")
    print(f"   sdiff('tags', 'languages') - разность: {difference}")
    print("   Разность возвращает элементы из первого множества, отсутствующие во втором")

    # Удаление элемента из множества
    print("\n6. Удаление элемента из множества:")
    client.srem("tags", "python")
    print("   Выполнено: srem('tags', 'python')")
    remaining_tags = client.smembers("tags")
    print(f"   Оставшиеся элементы: {remaining_tags}")

    # Очистка тестовых ключей
    client.delete("tags", "languages")
    print("\n   Тестовые ключи очищены")


def test_hashes(client: redis.Redis) -> None:
    """Тестирование работы с хэшами (Hashes) в Redis."""
    print("\n=== Тестирование Hashes (хэши) ===")

    # Установка нескольких полей в хэше
    print("\n1. Установка нескольких полей в хэше:")
    client.hset("user:1000", mapping={"name": "Иван", "age": "30", "city": "Москва"})
    print("   Выполнено: hset('user:1000', mapping={'name': 'Иван', 'age': '30', 'city': 'Москва'})")
    print("   Хэши удобны для хранения объектов с несколькими полями")

    # Установка одного поля в хэше
    print("\n2. Установка одного поля в хэше:")
    client.hset("user:1000", "email", "ivan@example.com")
    print("   Выполнено: hset('user:1000', 'email', 'ivan@example.com')")

    # Получение значения поля
    print("\n3. Получение значения поля:")
    name = client.hget("user:1000", "name")
    print(f"   hget('user:1000', 'name'): {name}")

    age = client.hget("user:1000", "age")
    print(f"   hget('user:1000', 'age'): {age}")

    # Получение всех полей и значений
    print("\n4. Получение всех полей и значений:")
    all_data = client.hgetall("user:1000")
    print(f"   hgetall('user:1000'): {all_data}")
    print("   Возвращает словарь со всеми полями и значениями")

    # Проверка существования поля
    print("\n5. Проверка существования поля:")
    exists = client.hexists("user:1000", "email")
    print(f"   hexists('user:1000', 'email'): {exists}")

    not_exists = client.hexists("user:1000", "phone")
    print(f"   hexists('user:1000', 'phone'): {not_exists}")

    # Получение всех ключей хэша
    print("\n6. Получение всех ключей хэша:")
    keys = client.hkeys("user:1000")
    print(f"   hkeys('user:1000'): {keys}")

    # Получение всех значений хэша
    print("\n7. Получение всех значений хэша:")
    values = client.hvals("user:1000")
    print(f"   hvals('user:1000'): {values}")

    # Удаление поля
    print("\n8. Удаление поля:")
    client.hdel("user:1000", "email")
    print("   Выполнено: hdel('user:1000', 'email')")
    remaining_data = client.hgetall("user:1000")
    print(f"   Оставшиеся данные: {remaining_data}")

    # Очистка тестовых ключей
    client.delete("user:1000")
    print("\n   Тестовые ключи очищены")


def test_sorted_sets(client: redis.Redis) -> None:
    """Тестирование работы с упорядоченными множествами (Sorted Sets) в Redis."""
    print("\n=== Тестирование Sorted Sets (упорядоченные множества) ===")

    # Добавление элементов с оценками (scores)
    print("\n1. Добавление элементов с оценками (scores):")
    client.zadd("leaderboard", {"player1": 100, "player2": 200, "player3": 150})
    print("   Выполнено: zadd('leaderboard', {'player1': 100, 'player2': 200, 'player3': 150})")
    print("   Упорядоченные множества хранят элементы с числовыми оценками для сортировки")

    # Получение элементов по индексу (от начала до конца)
    print("\n2. Получение элементов по индексу:")
    all_players = client.zrange("leaderboard", 0, -1)
    print(f"   zrange('leaderboard', 0, -1): {all_players}")
    print("   Возвращает элементы в порядке возрастания оценки (от меньшей к большей)")

    # Получение первых N элементов с оценками
    print("\n3. Получение первых N элементов с оценками:")
    top_players = client.zrange("leaderboard", 0, 2, withscores=True)
    print(f"   zrange('leaderboard', 0, 2, withscores=True): {top_players}")
    print("   Параметр withscores=True возвращает элементы вместе с их оценками")

    # Получение элементов в обратном порядке (по убыванию оценки)
    print("\n4. Получение элементов в обратном порядке (по убыванию):")
    reverse_players = client.zrevrange("leaderboard", 0, -1)
    print(f"   zrevrange('leaderboard', 0, -1): {reverse_players}")
    print("   zrevrange возвращает элементы в порядке убывания оценки (от большей к меньшей)")

    # Получение элементов по диапазону оценок
    print("\n5. Получение элементов по диапазону оценок:")
    players_by_score = client.zrangebyscore("leaderboard", 100, 200)
    print(f"   zrangebyscore('leaderboard', 100, 200): {players_by_score}")
    print("   Возвращает элементы с оценками от 100 до 200 включительно")

    # Получение ранга элемента (позиции в отсортированном списке)
    print("\n6. Получение ранга элемента:")
    rank = client.zrank("leaderboard", "player1")
    print(f"   zrank('leaderboard', 'player1'): {rank}")
    print("   Возвращает позицию элемента в отсортированном списке (0 - первое место)")

    rank_player2 = client.zrank("leaderboard", "player2")
    print(f"   zrank('leaderboard', 'player2'): {rank_player2}")

    # Получение оценки элемента
    print("\n7. Получение оценки элемента:")
    score = client.zscore("leaderboard", "player1")
    print(f"   zscore('leaderboard', 'player1'): {score}")

    score_player2 = client.zscore("leaderboard", "player2")
    print(f"   zscore('leaderboard', 'player2'): {score_player2}")

    # Удаление элемента
    print("\n8. Удаление элемента:")
    client.zrem("leaderboard", "player1")
    print("   Выполнено: zrem('leaderboard', 'player1')")
    remaining_players = client.zrange("leaderboard", 0, -1)
    print(f"   Оставшиеся игроки: {remaining_players}")

    # Очистка тестовых ключей
    client.delete("leaderboard")
    print("\n   Тестовые ключи очищены")
    print("\n   Применение: рейтинги, лидерборды, топ-списки")


def test_ttl(client: redis.Redis) -> None:
    """Тестирование работы с TTL (Time To Live) в Redis."""
    print("\n=== Тестирование TTL (Time To Live) ===")

    # Установка значения с TTL
    print("\n1. Установка значения с TTL (1 час = 3600 секунд):")
    client.setex("session:123", 3600, "active")
    print("   Выполнено: setex('session:123', 3600, 'active')")
    print("   setex устанавливает значение и TTL одновременно (атомарная операция)")

    # Проверка TTL
    ttl = client.ttl("session:123")
    print(f"   ttl('session:123'): {ttl} секунд")
    print("   Возвращает оставшееся время жизни ключа в секундах")

    # Установка TTL для существующего ключа
    print("\n2. Установка TTL для существующего ключа:")
    client.set("key", "value")
    print("   Создан ключ без TTL")
    initial_ttl = client.ttl("key")
    print(f"   ttl('key') до установки TTL: {initial_ttl}")
    print("   -1 означает, что TTL не установлен (ключ постоянный)")

    client.expire("key", 600)
    print("   Выполнено: expire('key', 600) - установлен TTL 10 минут (600 секунд)")
    new_ttl = client.ttl("key")
    print(f"   ttl('key') после установки TTL: {new_ttl} секунд")

    # Проверка TTL для несуществующего ключа
    print("\n3. Проверка TTL для несуществующего ключа:")
    non_existent_ttl = client.ttl("non_existent_key")
    print(f"   ttl('non_existent_key'): {non_existent_ttl}")
    print("   -2 означает, что ключ не существует")

    # Удаление TTL (сделать ключ постоянным)
    print("\n4. Удаление TTL (сделать ключ постоянным):")
    client.persist("key")
    print("   Выполнено: persist('key') - удален TTL")
    persistent_ttl = client.ttl("key")
    print(f"   ttl('key') после persist: {persistent_ttl}")
    print("   -1 означает, что ключ теперь постоянный (без TTL)")

    # Применение TTL для кэширования
    print("\n5. Применение TTL для кэширования:")
    print("   TTL позволяет автоматически удалять устаревшие данные из кэша")
    print("   Это полезно для:")
    print("   - Сессий пользователей (автоматическое истечение)")
    print("   - Временных токенов")
    print("   - Кэшированных данных с ограниченным временем актуальности")

    # Очистка тестовых ключей
    client.delete("session:123", "key")
    print("\n   Тестовые ключи очищены")


if __name__ == "__main__":
    import sys
    from datetime import datetime

    # Получение клиента Redis
    try:
        client = get_redis_client()
        print("✓ Подключение к Redis успешно установлено\n")
    except Exception as e:
        print(f"✗ Ошибка подключения к Redis: {e}")
        sys.exit(1)

    # Список тестов для выполнения
    tests = [
        ("Strings (строки)", test_strings),
        ("Lists (списки)", test_lists),
        ("Sets (множества)", test_sets),
        ("Hashes (хэши)", test_hashes),
        ("Sorted Sets (упорядоченные множества)", test_sorted_sets),
        ("TTL (Time To Live)", test_ttl),
    ]

    # Результаты тестирования
    results = []
    start_time = datetime.now()

    # Запуск тестов
    for test_name, test_func in tests:
        try:
            test_func(client)
            results.append({"name": test_name, "status": "✓ Успешно", "error": None})
        except Exception as e:
            results.append({"name": test_name, "status": "✗ Ошибка", "error": str(e)})

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Вывод сводки результатов
    print("\n" + "=" * 70)
    print(" " * 20 + "СВОДКА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    print(f"\nВремя выполнения: {duration:.2f} секунд")
    print(f"Дата и время: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "-" * 70)
    print(f"{'Тип данных':<40} {'Статус':<20} {'Детали':<10}")
    print("-" * 70)

    success_count = 0
    error_count = 0

    for result in results:
        status_icon = "✓" if "Успешно" in result["status"] else "✗"
        print(f"{result['name']:<40} {result['status']:<20}", end="")
        if result["error"]:
            print(f" {result['error']}")
            error_count += 1
        else:
            print(" -")
            success_count += 1

    print("-" * 70)
    print(f"\nВсего тестов: {len(results)}")
    print(f"Успешно: {success_count} ✓")
    print(f"Ошибок: {error_count} ✗")

    if error_count == 0:
        print("\n" + "=" * 70)
        print(" " * 25 + "ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print(" " * 20 + "ОБНАРУЖЕНЫ ОШИБКИ ПРИ ТЕСТИРОВАНИИ")
        print("=" * 70)

    print("\n=== Тестирование завершено ===")

