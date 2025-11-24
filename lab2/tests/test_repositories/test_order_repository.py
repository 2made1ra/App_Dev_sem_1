import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, User, Address, Product
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate, OrderUpdate, OrderItemCreate
from app.schemas.user_schema import UserCreate
from app.schemas.product_schema import ProductCreate


class TestOrderRepository:
    """Тесты для репозитория заказов."""

    @pytest.fixture
    async def test_user(
        self, session: AsyncSession, user_repository: UserRepository
    ) -> User:
        """Создает тестового пользователя."""
        user_data = UserCreate(
            email="order_test@example.com",
            username="order_test_user",
            description="User for order tests",
        )
        user = await user_repository.create(session, user_data)
        await session.flush()  # Используем flush вместо commit для изоляции
        return user

    @pytest.fixture
    async def test_address(
        self, session: AsyncSession, test_user: User
    ) -> Address:
        """Создает тестовый адрес."""
        address = Address(
            user_id=test_user.id,
            street="123 Test St",
            city="Test City",
            state="Test State",
            zip_code="12345",
            country="Test Country",
            is_primary=True,
        )
        session.add(address)
        await session.flush()
        await session.refresh(address)
        return address

    @pytest.fixture
    async def test_products(
        self, session: AsyncSession, product_repository: ProductRepository
    ) -> list[Product]:
        """Создает тестовые продукты."""
        products = []
        for i in range(3):
            product_data = ProductCreate(
                name=f"Test Product {i}",
                description=f"Description {i}",
                price=10.0 * (i + 1),
                stock_quantity=100,
            )
            product = await product_repository.create(session, product_data)
            products.append(product)
        await session.flush()  # Используем flush вместо commit для изоляции
        return products

    @pytest.mark.asyncio
    async def test_create_order(
        self,
        session: AsyncSession,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест создания заказа с несколькими продуктами."""
        # Создаем заказ с двумя продуктами
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=2),
            OrderItemCreate(product_id=test_products[1].id, quantity=1),
        ]
        total_price = (
            test_products[0].price * 2 + test_products[1].price * 1
        )

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
            status="pending",
        )

        order = await order_repository.create(session, order_data, total_price)
        await session.flush()  # Используем flush вместо commit для изоляции

        assert order.id is not None
        assert order.user_id == test_user.id
        assert order.delivery_address_id == test_address.id
        assert order.total_price == total_price
        assert order.status == "pending"
        assert len(order.items) == 2

        # Проверяем элементы заказа
        item1 = next(item for item in order.items if item.product_id == test_products[0].id)
        assert item1.quantity == 2
        assert item1.price_at_order == test_products[0].price

        item2 = next(item for item in order.items if item.product_id == test_products[1].id)
        assert item2.quantity == 1
        assert item2.price_at_order == test_products[1].price

    @pytest.mark.asyncio
    async def test_get_order_by_id(
        self,
        session: AsyncSession,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест получения заказа по ID с элементами."""
        # Создаем заказ
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=1),
        ]
        total_price = test_products[0].price * 1

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
        )

        created_order = await order_repository.create(session, order_data, total_price)
        await session.flush()  # Используем flush вместо commit для изоляции

        # Получаем заказ по ID
        found_order = await order_repository.get_by_id(session, created_order.id)

        assert found_order is not None
        assert found_order.id == created_order.id
        assert found_order.user_id == test_user.id
        assert len(found_order.items) == 1
        assert found_order.items[0].product_id == test_products[0].id

    @pytest.mark.asyncio
    async def test_get_order_by_id_not_found(
        self, session: AsyncSession, order_repository: OrderRepository
    ):
        """Тест получения несуществующего заказа по ID."""
        found_order = await order_repository.get_by_id(session, 99999)

        assert found_order is None

    @pytest.mark.asyncio
    async def test_update_order(
        self,
        session: AsyncSession,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест обновления заказа."""
        # Создаем заказ
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=1),
        ]
        total_price = test_products[0].price * 1

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
            status="pending",
        )

        created_order = await order_repository.create(session, order_data, total_price)
        await session.flush()  # Используем flush вместо commit для изоляции

        # Обновляем статус
        update_data = OrderUpdate(status="completed")
        updated_order = await order_repository.update(
            session, created_order.id, update_data
        )
        await session.flush()  # Используем flush вместо commit для изоляции

        assert updated_order.id == created_order.id
        assert updated_order.status == "completed"
        assert updated_order.user_id == test_user.id  # не изменилось
        assert len(updated_order.items) == 1  # items не изменились

    @pytest.mark.asyncio
    async def test_update_order_not_found(
        self, session: AsyncSession, order_repository: OrderRepository
    ):
        """Тест обновления несуществующего заказа."""
        update_data = OrderUpdate(status="completed")

        with pytest.raises(ValueError, match="Order with ID 99999 not found"):
            await order_repository.update(session, 99999, update_data)

    @pytest.mark.asyncio
    async def test_delete_order(
        self,
        session: AsyncSession,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест удаления заказа (items должны удалиться каскадно)."""
        # Создаем заказ
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=1),
        ]
        total_price = test_products[0].price * 1

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
        )

        created_order = await order_repository.create(session, order_data, total_price)
        await session.flush()  # Используем flush вместо commit для изоляции

        order_id = created_order.id
        
        await order_repository.delete(session, order_id)
        await session.flush()

        deleted_order = await order_repository.get_by_id(session, order_id)
        assert deleted_order is None

        # Проверяем, что items тоже удалены каскадно через ORM
        from sqlalchemy import select
        from app.models import OrderItem
        stmt = select(OrderItem).where(OrderItem.order_id == order_id)
        result = await session.execute(stmt)
        items = list(result.scalars().all())
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_delete_order_not_found(
        self, session: AsyncSession, order_repository: OrderRepository
    ):
        """Тест удаления несуществующего заказа."""
        with pytest.raises(ValueError, match="Order with ID 99999 not found"):
            await order_repository.delete(session, 99999)

    @pytest.mark.asyncio
    async def test_get_all_orders(
        self,
        session: AsyncSession,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест получения списка заказов."""
        # Создаем несколько заказов
        for i in range(3):
            order_items = [
                OrderItemCreate(product_id=test_products[0].id, quantity=i + 1),
            ]
            total_price = test_products[0].price * (i + 1)

            order_data = OrderCreate(
                user_id=test_user.id,
                delivery_address_id=test_address.id,
                items=order_items,
            )
            await order_repository.create(session, order_data, total_price)
        await session.flush()  # Используем flush вместо commit для изоляции

        orders = await order_repository.get_by_filter(session, count=10, page=1)
        total = await order_repository.count(session)

        assert len(orders) == 3
        assert total == 3
        # Проверяем, что items загружены
        for order in orders:
            assert hasattr(order, "items")

    @pytest.mark.asyncio
    async def test_get_orders_with_filters(
        self,
        session: AsyncSession,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест получения заказов с фильтрацией."""
        # Создаем заказы с разными статусами
        order_items = [OrderItemCreate(product_id=test_products[0].id, quantity=1)]
        total_price = test_products[0].price

        order1_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
            status="pending",
        )
        order2_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
            status="completed",
        )

        await order_repository.create(session, order1_data, total_price)
        await order_repository.create(session, order2_data, total_price)
        await session.flush()  # Используем flush вместо commit для изоляции

        # Фильтр по статусу
        orders = await order_repository.get_by_filter(
            session, count=10, page=1, status="pending"
        )
        assert len(orders) == 1
        assert orders[0].status == "pending"

        # Фильтр по user_id
        orders = await order_repository.get_by_filter(
            session, count=10, page=1, user_id=test_user.id
        )
        assert len(orders) == 2

    @pytest.mark.asyncio
    async def test_create_order_with_multiple_products(
        self,
        session: AsyncSession,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест создания заказа с несколькими продуктами."""
        # Создаем заказ со всеми тремя продуктами
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=2),
            OrderItemCreate(product_id=test_products[1].id, quantity=3),
            OrderItemCreate(product_id=test_products[2].id, quantity=1),
        ]
        total_price = (
            test_products[0].price * 2
            + test_products[1].price * 3
            + test_products[2].price * 1
        )

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
        )

        order = await order_repository.create(session, order_data, total_price)
        await session.flush()  # Используем flush вместо commit для изоляции

        assert len(order.items) == 3
        assert order.total_price == total_price

        # Проверяем каждый элемент заказа
        for i, item in enumerate(order.items):
            assert item.product_id == test_products[i].id
            assert item.quantity == order_items[i].quantity
            assert item.price_at_order == test_products[i].price

