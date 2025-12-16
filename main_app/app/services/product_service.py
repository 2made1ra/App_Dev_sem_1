import logging
from datetime import datetime

import redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.product_cache import (
    delete_product_from_cache,
    get_product_from_cache,
    set_product_to_cache,
    update_product_in_cache,
)
from app.models import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import ProductCreate, ProductResponse, ProductUpdate

logger = logging.getLogger(__name__)


class ProductService:
    """Сервис для бизнес-логики работы с продуктами."""

    def __init__(
        self,
        product_repository: ProductRepository,
        redis_client: redis.Redis | None = None,
    ):
        """
        Инициализация сервиса.
        Args:
            product_repository: Репозиторий для работы с продуктами (Dependency Injection)
            redis_client: Клиент Redis для кэширования (опционально)
        """
        self.product_repository = product_repository
        self.redis_client = redis_client

    async def get_by_id(self, session: AsyncSession, product_id: int) -> Product | None:
        """
        Получить продукт по ID с использованием кэширования.
        Args:
            session: Асинхронная сессия базы данных
            product_id: ID продукта (int)

        Returns:
            Product объект или None, если не найден
        """
        # Попытка получить данные из кэша
        if self.redis_client:
            cached_data = get_product_from_cache(self.redis_client, product_id)
            if cached_data is not None:
                # Преобразуем словарь обратно в объект Product
                # Преобразуем строки ISO формата обратно в datetime
                created_at = (
                    datetime.fromisoformat(cached_data["created_at"])
                    if isinstance(cached_data["created_at"], str)
                    else cached_data["created_at"]
                )
                updated_at = (
                    datetime.fromisoformat(cached_data["updated_at"])
                    if cached_data.get("updated_at")
                    and isinstance(cached_data["updated_at"], str)
                    else cached_data.get("updated_at")
                )
                return Product(
                    id=cached_data["id"],
                    name=cached_data["name"],
                    description=cached_data.get("description"),
                    price=cached_data["price"],
                    stock_quantity=cached_data["stock_quantity"],
                    created_at=created_at,
                    updated_at=updated_at,
                )

        # Если данных нет в кэше, получаем из БД
        product = await self.product_repository.get_by_id(session, product_id)
        if product and self.redis_client:
            # Сохраняем в кэш (обработка ошибок внутри функции)
            try:
                product_dict = ProductResponse.model_validate(product).model_dump()
                # Преобразуем datetime в строки для JSON
                if product_dict.get("created_at"):
                    product_dict["created_at"] = product_dict["created_at"].isoformat()
                if product_dict.get("updated_at"):
                    product_dict["updated_at"] = product_dict["updated_at"].isoformat()
                set_product_to_cache(self.redis_client, product_id, product_dict)
            except (ValueError, TypeError, redis.RedisError) as e:
                # Логируем ошибку, но не блокируем возврат данных
                logger.warning(
                    "Не удалось сохранить продукцию в кэш: product_id=%s, error=%s",
                    product_id,
                    e,
                )

        return product

    async def get_by_filter(
        self, session: AsyncSession, count: int, page: int, **kwargs
    ) -> list[Product]:
        """
        Получить список продуктов с пагинацией и фильтрацией.
        Args:
            session: Асинхронная сессия базы данных
            count: Количество записей на странице
            page: Номер страницы (начинается с 1)
            **kwargs: Фильтры (name, min_price, max_price)

        Returns:
            Список продуктов
        """
        return await self.product_repository.get_by_filter(
            session, count, page, **kwargs
        )

    async def create(
        self, session: AsyncSession, product_data: ProductCreate
    ) -> Product:
        """
        Создать новый продукт.
        Args:
            session: Асинхронная сессия базы данных
            product_data: Данные для создания продукта

        Returns:
            Созданный объект Product

        Raises:
            ValueError: Если данные невалидны
        """
        # Валидация цены
        if product_data.price <= 0:
            raise ValueError("Price must be greater than 0")

        # Валидация количества на складе
        if product_data.stock_quantity < 0:
            raise ValueError("Stock quantity cannot be negative")

        product = await self.product_repository.create(session, product_data)
        await session.commit()
        return product

    async def update(
        self, session: AsyncSession, product_id: int, product_data: ProductUpdate
    ) -> Product:
        """
        Обновить продукт.
        Args:
            session: Асинхронная сессия базы данных
            product_id: ID продукта (int)
            product_data: Данные для обновления

        Returns:
            Обновленный объект Product

        Raises:
            ValueError: Если продукт не найден или данные невалидны
        """
        existing_product = await self.product_repository.get_by_id(session, product_id)
        if not existing_product:
            raise ValueError(f"Product with ID {product_id} not found")

        # Валидация цены, если она обновляется
        if product_data.price is not None and product_data.price <= 0:
            raise ValueError("Price must be greater than 0")

        # Валидация количества на складе, если оно обновляется
        if product_data.stock_quantity is not None and product_data.stock_quantity < 0:
            raise ValueError("Stock quantity cannot be negative")

        product = await self.product_repository.update(
            session, product_id, product_data
        )
        await session.commit()

        # Обновление кэша после обновления продукции (обработка ошибок внутри функции)
        if self.redis_client:
            try:
                product_dict = ProductResponse.model_validate(product).model_dump()
                # Преобразуем datetime в строки для JSON
                if product_dict.get("created_at"):
                    product_dict["created_at"] = product_dict["created_at"].isoformat()
                if product_dict.get("updated_at"):
                    product_dict["updated_at"] = product_dict["updated_at"].isoformat()
                update_product_in_cache(self.redis_client, product_id, product_dict)
            except (ValueError, TypeError, redis.RedisError) as e:
                # Логируем ошибку, но не блокируем возврат данных
                logger.warning(
                    "Не удалось обновить продукцию в кэше: product_id=%s, error=%s",
                    product_id,
                    e,
                )

        return product

    async def delete(self, session: AsyncSession, product_id: int) -> None:
        """
        Удалить продукт.
        Args:
            session: Асинхронная сессия базы данных
            product_id: ID продукта (int)

        Raises:
            ValueError: Если продукт не найден
        """
        await self.product_repository.delete(session, product_id)
        await session.commit()

        # Инвалидация кэша после удаления (обработка ошибок внутри функции)
        if self.redis_client:
            try:
                delete_product_from_cache(self.redis_client, product_id)
            except redis.RedisError as e:
                # Логируем ошибку, но не блокируем удаление
                logger.warning(
                    "Не удалось удалить продукцию из кэша: product_id=%s, error=%s",
                    product_id,
                    e,
                )

    async def count(self, session: AsyncSession, **kwargs) -> int:
        """
        Получить общее количество продуктов с учетом фильтров.
        Args:
            session: Асинхронная сессия базы данных
            **kwargs: Фильтры (name, min_price, max_price)

        Returns:
            Количество продуктов
        """
        return await self.product_repository.count(session, **kwargs)
