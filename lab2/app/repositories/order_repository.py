from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order, OrderItem
from app.schemas.order_schema import OrderCreate, OrderUpdate


class OrderRepository:
    """Репозиторий для CRUD операций с заказами."""

    async def get_by_id(self, session: AsyncSession, order_id: int) -> Order | None:
        """
        Получить заказ по ID с элементами заказа.

        Args:
            session: Асинхронная сессия базы данных
            order_id: ID заказа (int)

        Returns:
            Order объект с загруженными items или None, если не найден
        """
        stmt = (
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_filter(
        self, session: AsyncSession, count: int, page: int, **kwargs
    ) -> list[Order]:
        """
        Получить список заказов с пагинацией и фильтрацией.

        Args:
            session: Асинхронная сессия базы данных
            count: Количество записей на странице
            page: Номер страницы (начинается с 1)
            **kwargs: Фильтры (user_id, status)

        Returns:
            Список заказов с загруженными items
        """
        stmt = select(Order).options(selectinload(Order.items))

        if "user_id" in kwargs and kwargs["user_id"] is not None:
            stmt = stmt.where(Order.user_id == kwargs["user_id"])
        if "status" in kwargs and kwargs["status"]:
            stmt = stmt.where(Order.status == kwargs["status"])

        offset = (page - 1) * count
        stmt = stmt.offset(offset).limit(count)

        stmt = stmt.order_by(Order.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self, session: AsyncSession, order_data: OrderCreate, total_price: float
    ) -> Order:
        """
        Создать новый заказ с несколькими продуктами.

        Args:
            session: Асинхронная сессия базы данных
            order_data: Данные для создания заказа
            total_price: Общая стоимость заказа (вычисляется в сервисе)

        Returns:
            Созданный объект Order с загруженными items
        """
        order = Order(
            user_id=order_data.user_id,
            delivery_address_id=order_data.delivery_address_id,
            total_price=total_price,
            status=order_data.status or "pending",
        )
        session.add(order)
        await session.flush()

        # Создаем элементы заказа
        for item_data in order_data.items:
            # Получаем продукт для сохранения цены на момент заказа
            from app.models import Product

            product_stmt = select(Product).where(Product.id == item_data.product_id)
            product_result = await session.execute(product_stmt)
            product = product_result.scalar_one_or_none()

            if not product:
                raise ValueError(f"Product with ID {item_data.product_id} not found")

            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                price_at_order=product.price,
            )
            session.add(order_item)

        await session.flush()
        await session.refresh(order)

        # Загружаем items для возврата
        stmt = (
            select(Order).where(Order.id == order.id).options(selectinload(Order.items))
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def update(
        self, session: AsyncSession, order_id: int, order_data: OrderUpdate
    ) -> Order:
        """
        Обновить заказ через ORM.

        Args:
            session: Асинхронная сессия базы данных
            order_id: ID заказа (int)
            order_data: Данные для обновления (только переданные поля)

        Returns:
            Обновленный объект Order с загруженными items

        Raises:
            ValueError: Если заказ не найден
        """
        # Получаем объект заказа через ORM
        order = await self.get_by_id(session, order_id)

        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        # Обновляем атрибуты объекта через ORM
        update_data = {
            k: v
            for k, v in order_data.model_dump(exclude_unset=True).items()
            if v is not None
        }

        for key, value in update_data.items():
            setattr(order, key, value)

        await session.flush()

        # Перезагружаем объект с items для возврата
        updated_order = await self.get_by_id(session, order_id)
        return updated_order

    async def delete(self, session: AsyncSession, order_id: int) -> None:
        """
        Удалить заказ (items удалятся каскадно через ORM).

        Args:
            session: Асинхронная сессия базы данных
            order_id: ID заказа (int)

        Raises:
            ValueError: Если заказ не найден
        """
        # Получаем объект заказа с загруженными items для каскадного удаления
        order = await self.get_by_id(session, order_id)

        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        # Используем ORM delete - каскадное удаление сработает автоматически
        await session.delete(order)
        await session.flush()

    async def count(self, session: AsyncSession, **kwargs) -> int:
        """
        Получить общее количество заказов с учетом фильтров.

        Args:
            session: Асинхронная сессия базы данных
            **kwargs: Фильтры (user_id, status)

        Returns:
            Количество заказов
        """
        stmt = select(func.count(Order.id))

        if "user_id" in kwargs and kwargs["user_id"] is not None:
            stmt = stmt.where(Order.user_id == kwargs["user_id"])
        if "status" in kwargs and kwargs["status"]:
            stmt = stmt.where(Order.status == kwargs["status"])

        result = await session.execute(stmt)
        return result.scalar_one() or 0
