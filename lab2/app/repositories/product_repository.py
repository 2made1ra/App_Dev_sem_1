from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Product
from app.schemas.product_schema import ProductCreate, ProductUpdate


class ProductRepository:
    """Репозиторий для CRUD операций с продуктами."""

    async def get_by_id(self, session: AsyncSession, product_id: int) -> Product | None:
        """
        Получить продукт по ID.

        Args:
            session: Асинхронная сессия базы данных
            product_id: ID продукта (int)

        Returns:
            Product объект или None, если не найден
        """
        stmt = select(Product).where(Product.id == product_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

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
        stmt = select(Product)

        if "name" in kwargs and kwargs["name"]:
            stmt = stmt.where(Product.name.ilike(f"%{kwargs['name']}%"))
        if "min_price" in kwargs and kwargs["min_price"] is not None:
            stmt = stmt.where(Product.price >= kwargs["min_price"])
        if "max_price" in kwargs and kwargs["max_price"] is not None:
            stmt = stmt.where(Product.price <= kwargs["max_price"])

        offset = (page - 1) * count
        stmt = stmt.offset(offset).limit(count)

        stmt = stmt.order_by(Product.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

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
        """
        product = Product(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            stock_quantity=product_data.stock_quantity,
        )
        session.add(product)
        await session.flush()
        await session.refresh(product)
        return product

    async def update(
        self, session: AsyncSession, product_id: int, product_data: ProductUpdate
    ) -> Product:
        """
        Обновить продукт через ORM.

        Args:
            session: Асинхронная сессия базы данных
            product_id: ID продукта (int)
            product_data: Данные для обновления (только переданные поля)

        Returns:
            Обновленный объект Product

        Raises:
            ValueError: Если продукт не найден
        """
        # Получаем объект продукта через ORM
        product = await self.get_by_id(session, product_id)

        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        # Обновляем атрибуты объекта через ORM
        update_data = {
            k: v
            for k, v in product_data.model_dump(exclude_unset=True).items()
            if v is not None
        }

        for key, value in update_data.items():
            setattr(product, key, value)

        await session.flush()
        await session.refresh(product)
        return product

    async def delete(self, session: AsyncSession, product_id: int) -> None:
        """
        Удалить продукт через ORM.

        Args:
            session: Асинхронная сессия базы данных
            product_id: ID продукта (int)

        Raises:
            ValueError: Если продукт не найден
        """
        product = await self.get_by_id(session, product_id)

        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        # Используем ORM delete
        await session.delete(product)
        await session.flush()

    async def count(self, session: AsyncSession, **kwargs) -> int:
        """
        Получить общее количество продуктов с учетом фильтров.

        Args:
            session: Асинхронная сессия базы данных
            **kwargs: Фильтры (name, min_price, max_price)

        Returns:
            Количество продуктов
        """
        stmt = select(func.count(Product.id))

        if "name" in kwargs and kwargs["name"]:
            stmt = stmt.where(Product.name.ilike(f"%{kwargs['name']}%"))
        if "min_price" in kwargs and kwargs["min_price"] is not None:
            stmt = stmt.where(Product.price >= kwargs["min_price"])
        if "max_price" in kwargs and kwargs["max_price"] is not None:
            stmt = stmt.where(Product.price <= kwargs["max_price"])

        result = await session.execute(stmt)
        return result.scalar_one() or 0
