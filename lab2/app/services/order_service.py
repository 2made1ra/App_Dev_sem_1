from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Order, Product, User, Address
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate, OrderUpdate


class OrderService:
    """Сервис для бизнес-логики работы с заказами."""

    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
    ):
        """
        Инициализация сервиса.
        Args:
            order_repository: Репозиторий для работы с заказами (Dependency Injection)
            product_repository: Репозиторий для работы с продуктами (Dependency Injection)
        """
        self.order_repository = order_repository
        self.product_repository = product_repository

    async def get_by_id(
        self, session: AsyncSession, order_id: int
    ) -> Order | None:
        """
        Получить заказ по ID.
        Args:
            session: Асинхронная сессия базы данных
            order_id: ID заказа (int)
            
        Returns:
            Order объект или None, если не найден
        """
        return await self.order_repository.get_by_id(session, order_id)

    async def get_by_filter(
        self,
        session: AsyncSession,
        count: int,
        page: int,
        **kwargs
    ) -> list[Order]:
        """
        Получить список заказов с пагинацией и фильтрацией.
        Args:
            session: Асинхронная сессия базы данных
            count: Количество записей на странице
            page: Номер страницы (начинается с 1)
            **kwargs: Фильтры (user_id, status)
            
        Returns:
            Список заказов
        """
        return await self.order_repository.get_by_filter(
            session, count, page, **kwargs
        )

    async def create(
        self, session: AsyncSession, order_data: OrderCreate
    ) -> Order:
        """
        Создать новый заказ с проверкой наличия товаров и расчетом общей стоимости.
        Args:
            session: Асинхронная сессия базы данных
            order_data: Данные для создания заказа
            
        Returns:
            Созданный объект Order
            
        Raises:
            ValueError: Если пользователь, адрес или продукт не найдены, или недостаточно товара на складе
        """
        # Проверка существования пользователя
        user_stmt = select(User).where(User.id == order_data.user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with ID {order_data.user_id} not found")

        # Проверка существования адреса доставки
        address_stmt = select(Address).where(Address.id == order_data.delivery_address_id)
        address_result = await session.execute(address_stmt)
        address = address_result.scalar_one_or_none()
        if not address:
            raise ValueError(f"Address with ID {order_data.delivery_address_id} not found")

        # Проверка, что адрес принадлежит пользователю
        if address.user_id != order_data.user_id:
            raise ValueError("Delivery address does not belong to the user")

        # Проверка наличия товаров и расчет общей стоимости
        total_price = 0.0
        products_to_update = []  # Для обновления количества на складе

        for item_data in order_data.items:
            # Получаем продукт
            product = await self.product_repository.get_by_id(session, item_data.product_id)
            if not product:
                raise ValueError(f"Product with ID {item_data.product_id} not found")

            # Проверка наличия достаточного количества товара
            if product.stock_quantity < item_data.quantity:
                raise ValueError(
                    f"Insufficient stock for product {product.name}. "
                    f"Available: {product.stock_quantity}, Requested: {item_data.quantity}"
                )

            # Расчет стоимости для этого элемента
            item_total = product.price * item_data.quantity
            total_price += item_total

            # Сохраняем информацию для обновления количества на складе
            products_to_update.append((product, item_data.quantity))

        # Создаем заказ
        order = await self.order_repository.create(session, order_data, total_price)

        # Обновляем количество товаров на складе
        for product, quantity in products_to_update:
            product.stock_quantity -= quantity
            session.add(product)

        await session.commit()
        await session.refresh(order)
        
        # Загружаем items для возврата (нужно для Pydantic валидации)
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items))
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def update(
        self,
        session: AsyncSession,
        order_id: int,
        order_data: OrderUpdate
    ) -> Order:
        """
        Обновить заказ (в основном статус).
        Args:
            session: Асинхронная сессия базы данных
            order_id: ID заказа (int)
            order_data: Данные для обновления
            
        Returns:
            Обновленный объект Order
            
        Raises:
            ValueError: Если заказ не найден
        """
        existing_order = await self.order_repository.get_by_id(session, order_id)
        if not existing_order:
            raise ValueError(f"Order with ID {order_id} not found")

        order = await self.order_repository.update(session, order_id, order_data)
        await session.commit()
        return order

    async def delete(
        self, session: AsyncSession, order_id: int
    ) -> None:
        """
        Удалить заказ.
        Args:
            session: Асинхронная сессия базы данных
            order_id: ID заказа (int)
            
        Raises:
            ValueError: Если заказ не найден
        """
        await self.order_repository.delete(session, order_id)
        await session.commit()

    async def count(
        self, session: AsyncSession, **kwargs
    ) -> int:
        """
        Получить общее количество заказов с учетом фильтров.
        Args:
            session: Асинхронная сессия базы данных
            **kwargs: Фильтры (user_id, status)
            
        Returns:
            Количество заказов
        """
        return await self.order_repository.count(session, **kwargs)

