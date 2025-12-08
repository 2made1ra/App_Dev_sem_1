import redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.redis_client import get_redis_client
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.user_service import UserService


def provide_redis_client() -> redis.Redis:
    """
    Провайдер клиента Redis.

    Создает и возвращает клиент Redis с использованием настроек из переменных окружения.
    Клиент создается при каждом запросе (stateless).

    Returns:
        redis.Redis: Экземпляр клиента Redis
    """
    return get_redis_client()


async def provide_db_session() -> AsyncSession:
    """
    Провайдер сессии базы данных.

    Использует async context manager для управления жизненным циклом сессии.
    Сессия автоматически закрывается после завершения запроса.

    Yields:
        AsyncSession: Асинхронная сессия базы данных
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def provide_user_repository(db_session: AsyncSession) -> UserRepository:
    """
    Провайдер репозитория пользователей.

    Args:
        db_session: Сессия базы данных (внедряется через DI)

    Returns:
        UserRepository: Экземпляр репозитория пользователей
    """
    return UserRepository()


async def provide_user_service(
    user_repository: UserRepository, redis_client: redis.Redis
) -> UserService:
    """
    Провайдер сервиса пользователей.

    Args:
        user_repository: Репозиторий пользователей (внедряется через DI)
        redis_client: Клиент Redis для кэширования (внедряется через DI)

    Returns:
        UserService: Экземпляр сервиса пользователей
    """
    return UserService(user_repository, redis_client)


async def provide_product_repository(db_session: AsyncSession) -> ProductRepository:
    """
    Провайдер репозитория продуктов.

    Args:
        db_session: Сессия базы данных (внедряется через DI)

    Returns:
        ProductRepository: Экземпляр репозитория продуктов
    """
    return ProductRepository()


async def provide_product_service(
    product_repository: ProductRepository, redis_client: redis.Redis
) -> ProductService:
    """
    Провайдер сервиса продуктов.

    Args:
        product_repository: Репозиторий продуктов (внедряется через DI)
        redis_client: Клиент Redis для кэширования (внедряется через DI)

    Returns:
        ProductService: Экземпляр сервиса продуктов
    """
    return ProductService(product_repository, redis_client)


async def provide_order_repository(db_session: AsyncSession) -> OrderRepository:
    """
    Провайдер репозитория заказов.

    Args:
        db_session: Сессия базы данных (внедряется через DI)

    Returns:
        OrderRepository: Экземпляр репозитория заказов
    """
    return OrderRepository()


async def provide_order_service(
    order_repository: OrderRepository,
    product_repository: ProductRepository,
) -> OrderService:
    """
    Провайдер сервиса заказов.

    Args:
        order_repository: Репозиторий заказов (внедряется через DI)
        product_repository: Репозиторий продуктов (внедряется через DI)

    Returns:
        OrderService: Экземпляр сервиса заказов
    """
    return OrderService(order_repository, product_repository)
