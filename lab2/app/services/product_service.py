from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import ProductCreate, ProductUpdate


class ProductService:
    """Сервис для бизнес-логики работы с продуктами."""

    def __init__(self, product_repository: ProductRepository):
        """
        Инициализация сервиса.
        Args:
            product_repository: Репозиторий для работы с продуктами (Dependency Injection)
        """
        self.product_repository = product_repository

    async def get_by_id(
        self, session: AsyncSession, product_id: int
    ) -> Product | None:
        """
        Получить продукт по ID.
        Args:
            session: Асинхронная сессия базы данных
            product_id: ID продукта (int)
            
        Returns:
            Product объект или None, если не найден
        """
        return await self.product_repository.get_by_id(session, product_id)

    async def get_by_filter(
        self,
        session: AsyncSession,
        count: int,
        page: int,
        **kwargs
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
        self,
        session: AsyncSession,
        product_id: int,
        product_data: ProductUpdate
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

        product = await self.product_repository.update(session, product_id, product_data)
        await session.commit()
        return product

    async def delete(
        self, session: AsyncSession, product_id: int
    ) -> None:
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

    async def count(
        self, session: AsyncSession, **kwargs
    ) -> int:
        """
        Получить общее количество продуктов с учетом фильтров.
        Args:
            session: Асинхронная сессия базы данных
            **kwargs: Фильтры (name, min_price, max_price)
            
        Returns:
            Количество продуктов
        """
        return await self.product_repository.count(session, **kwargs)

