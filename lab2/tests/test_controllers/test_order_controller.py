import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from litestar.testing import TestClient

from app.models import User, Address, Product, Order
from app.schemas.user_schema import UserCreate
from app.schemas.product_schema import ProductCreate
from app.repositories.user_repository import UserRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository


class TestOrderController:
    """Тесты для API эндпоинтов заказов."""

    @pytest.fixture
    async def test_user(
        self, session, user_repository: UserRepository
    ) -> User:
        """Создает тестового пользователя."""
        user_data = UserCreate(
            email="order_test@example.com",
            username="order_test_user",
        )
        user = await user_repository.create(session, user_data)
        await session.commit()
        return user

    @pytest.fixture
    async def test_address(
        self, session, test_user: User
    ) -> Address:
        """Создает тестовый адрес."""
        from app.models import Address
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
        await session.commit()
        return address

    @pytest.fixture
    async def test_products(
        self, session, product_repository: ProductRepository
    ) -> list[Product]:
        """Создает тестовые продукты."""
        products = []
        for i in range(3):
            product_data = ProductCreate(
                name=f"Test Product {i}",
                price=10.0 * (i + 1),
                stock_quantity=100,
            )
            product = await product_repository.create(session, product_data)
            products.append(product)
        await session.commit()
        return products

    @pytest.mark.asyncio
    async def test_get_order_by_id(
        self,
        client: TestClient,
        session,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест GET /orders/{order_id} - получение заказа по ID."""
        # Создаем заказ
        from app.schemas.order_schema import OrderCreate, OrderItemCreate
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=2),
        ]
        total_price = test_products[0].price * 2

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
        )

        created_order = await order_repository.create(session, order_data, total_price)
        await session.commit()

        # Делаем запрос к API
        response = client.get(f"/orders/{created_order.id}")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == created_order.id
        assert data["user_id"] == test_user.id
        assert data["total_price"] == total_price
        assert "items" in data
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_order_by_id_not_found(self, client: TestClient):
        """Тест GET /orders/{order_id} - несуществующий заказ."""
        response = client.get("/orders/99999")

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_all_orders(
        self,
        client: TestClient,
        session,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест GET /orders - получение списка заказов."""
        # Создаем несколько заказов
        from app.schemas.order_schema import OrderCreate, OrderItemCreate
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
        await session.commit()

        response = client.get("/orders")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "orders" in data
        assert "total" in data
        assert len(data["orders"]) >= 3
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_create_order(
        self,
        client: TestClient,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест POST /orders - создание заказа с несколькими продуктами."""
        order_data = {
            "user_id": test_user.id,
            "delivery_address_id": test_address.id,
            "items": [
                {"product_id": test_products[0].id, "quantity": 2},
                {"product_id": test_products[1].id, "quantity": 1},
            ],
            "status": "pending",
        }

        response = client.post("/orders", json=order_data)

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["delivery_address_id"] == test_address.id
        assert data["status"] == "pending"
        assert "items" in data
        assert len(data["items"]) == 2
        assert "total_price" in data
        assert data["total_price"] > 0

    @pytest.mark.asyncio
    async def test_create_order_insufficient_stock(
        self,
        client: TestClient,
        session,
        product_repository: ProductRepository,
        test_user: User,
        test_address: Address,
    ):
        """Тест POST /orders - обработка ошибки недостаточного количества товара."""
        # Создаем продукт с малым количеством на складе
        product_data = ProductCreate(
            name="Low Stock Product",
            price=100.0,
            stock_quantity=5,  # Доступно только 5
        )
        product = await product_repository.create(session, product_data)
        await session.commit()

        order_data = {
            "user_id": test_user.id,
            "delivery_address_id": test_address.id,
            "items": [
                {"product_id": product.id, "quantity": 10},  # Заказываем 10, а есть только 5
            ],
        }

        response = client.post("/orders", json=order_data)

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert "insufficient stock" in data["detail"].lower() or "available" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_order(
        self,
        client: TestClient,
        session,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест PUT /orders/{order_id} - обновление заказа."""
        # Создаем заказ
        from app.schemas.order_schema import OrderCreate, OrderItemCreate
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=1),
        ]
        total_price = test_products[0].price

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
            status="pending",
        )

        created_order = await order_repository.create(session, order_data, total_price)
        await session.commit()

        # Обновляем статус заказа
        update_data = {
            "status": "completed",
        }

        response = client.put(f"/orders/{created_order.id}", json=update_data)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == created_order.id
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_order_not_found(self, client: TestClient):
        """Тест PUT /orders/{order_id} - обновление несуществующего заказа."""
        update_data = {"status": "completed"}

        response = client.put("/orders/99999", json=update_data)

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_order(
        self,
        client: TestClient,
        session,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест DELETE /orders/{order_id} - удаление заказа."""
        # Создаем заказ
        from app.schemas.order_schema import OrderCreate, OrderItemCreate
        order_items = [
            OrderItemCreate(product_id=test_products[0].id, quantity=1),
        ]
        total_price = test_products[0].price

        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=order_items,
        )

        created_order = await order_repository.create(session, order_data, total_price)
        await session.commit()

        # Удаляем заказ
        response = client.delete(f"/orders/{created_order.id}")

        assert response.status_code == HTTP_204_NO_CONTENT

        # Проверяем, что заказ удален
        get_response = client.get(f"/orders/{created_order.id}")
        assert get_response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_order_not_found(self, client: TestClient):
        """Тест DELETE /orders/{order_id} - удаление несуществующего заказа."""
        response = client.delete("/orders/99999")

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_orders_with_filters(
        self,
        client: TestClient,
        session,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_products: list[Product],
    ):
        """Тест GET /orders - фильтрация."""
        # Создаем заказы с разными статусами
        from app.schemas.order_schema import OrderCreate, OrderItemCreate
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
        await session.commit()

        # Фильтр по статусу
        response = client.get("/orders?status=pending")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert all(order["status"] == "pending" for order in data["orders"])

        # Фильтр по user_id
        response = client.get(f"/orders?user_id={test_user.id}")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert all(order["user_id"] == test_user.id for order in data["orders"])

