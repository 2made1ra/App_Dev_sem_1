import pytest
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Product, User, Address, OrderItem
from app.services.order_service import OrderService
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate, OrderUpdate, OrderItemCreate


class TestOrderService:
    """Тесты для сервиса заказов с моками."""

    @pytest.fixture
    def mock_order_repository(self):
        """Создает мок репозитория заказов."""
        return AsyncMock(spec=OrderRepository)

    @pytest.fixture
    def mock_product_repository(self):
        """Создает мок репозитория продуктов."""
        return AsyncMock(spec=ProductRepository)

    @pytest.fixture
    def mock_session(self):
        """Создает мок сессии БД."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.add = Mock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def order_service(self, mock_order_repository, mock_product_repository):
        """Создает экземпляр сервиса с моками репозиториев."""
        return OrderService(mock_order_repository, mock_product_repository)

    @pytest.mark.asyncio
    async def test_create_order_success(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
        mock_product_repository,
    ):
        """Тест успешного создания заказа."""
        # Мокаем пользователя
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = "test@example.com"

        # Мокаем адрес
        mock_address = Mock(spec=Address)
        mock_address.id = 1
        mock_address.user_id = 1  # Адрес принадлежит пользователю

        # Мокаем продукты
        mock_product1 = Mock(spec=Product)
        mock_product1.id = 1
        mock_product1.name = "Product 1"
        mock_product1.price = 100.0
        mock_product1.stock_quantity = 10

        mock_product2 = Mock(spec=Product)
        mock_product2.id = 2
        mock_product2.name = "Product 2"
        mock_product2.price = 50.0
        mock_product2.stock_quantity = 5

        # Мокаем элементы заказа
        mock_item1 = Mock(spec=OrderItem)
        mock_item1.product_id = 1
        mock_item1.quantity = 2
        mock_item1.price_at_order = 100.0

        mock_item2 = Mock(spec=OrderItem)
        mock_item2.product_id = 2
        mock_item2.quantity = 1
        mock_item2.price_at_order = 50.0

        # Мокаем заказ
        mock_order = Mock(spec=Order)
        mock_order.id = 1
        mock_order.user_id = 1
        mock_order.delivery_address_id = 1
        mock_order.total_price = 250.0  # 100*2 + 50*1
        mock_order.status = "pending"
        mock_order.items = [mock_item1, mock_item2]

        # Настраиваем моки для session.execute (для проверки User, Address и Order)
        execute_call_count = 0
        
        async def mock_execute(stmt):
            nonlocal execute_call_count
            result_mock = Mock()
            stmt_str = str(stmt).lower()
            execute_call_count += 1
            
            # Определяем, что возвращать на основе запроса
            # Порядок важен: сначала проверяем Order (может содержать "user" в "delivery_address")
            if "orders" in stmt_str and execute_call_count > 2:
                # Для запроса Order (после проверки User и Address) возвращаем через scalar_one
                result_mock.scalar_one = Mock(return_value=mock_order)
            elif "users" in stmt_str or (execute_call_count == 1 and "user" in stmt_str and "order" not in stmt_str):
                # Первый вызов - проверка User
                result_mock.scalar_one_or_none = Mock(return_value=mock_user)
            elif "addresses" in stmt_str or (execute_call_count == 2 and "address" in stmt_str and "order" not in stmt_str):
                # Второй вызов - проверка Address
                result_mock.scalar_one_or_none = Mock(return_value=mock_address)
            else:
                result_mock.scalar_one_or_none = Mock(return_value=None)
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        # Настраиваем моки репозиториев
        mock_product_repository.get_by_id.side_effect = [mock_product1, mock_product2]
        mock_order_repository.create.return_value = mock_order

        # Создаем данные заказа
        order_data = OrderCreate(
            user_id=1,
            delivery_address_id=1,
            items=[
                OrderItemCreate(product_id=1, quantity=2),
                OrderItemCreate(product_id=2, quantity=1),
            ],
        )

        result = await order_service.create(mock_session, order_data)

        assert result is not None
        assert result.id == 1
        assert result.total_price == 250.0
        assert len(result.items) == 2

        # Проверяем, что продукты были получены
        assert mock_product_repository.get_by_id.call_count == 2
        mock_product_repository.get_by_id.assert_any_call(mock_session, 1)
        mock_product_repository.get_by_id.assert_any_call(mock_session, 2)

        # Проверяем, что заказ был создан
        mock_order_repository.create.assert_called_once()
        call_args = mock_order_repository.create.call_args
        assert call_args[0][1] == order_data
        assert call_args[0][2] == 250.0  # total_price

        # Проверяем, что количество товара было обновлено
        assert mock_product1.stock_quantity == 8  # 10 - 2
        assert mock_product2.stock_quantity == 4  # 5 - 1
        assert mock_session.add.call_count == 2  # Оба продукта были добавлены для обновления

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_insufficient_stock(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
        mock_product_repository,
    ):
        """Тест создания заказа с недостаточным количеством товара."""
        mock_user = Mock(spec=User)
        mock_user.id = 1

        mock_address = Mock(spec=Address)
        mock_address.id = 1
        mock_address.user_id = 1

        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.name = "Product 1"
        mock_product.price = 100.0
        mock_product.stock_quantity = 5  # Доступно только 5

        async def mock_execute(stmt):
            result_mock = Mock()
            if "users" in str(stmt).lower() or "User" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_user
            elif "addresses" in str(stmt).lower() or "Address" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_address
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_product_repository.get_by_id.return_value = mock_product

        order_data = OrderCreate(
            user_id=1,
            delivery_address_id=1,
            items=[OrderItemCreate(product_id=1, quantity=10)],  # Заказываем 10, а есть только 5
        )

        with pytest.raises(
            ValueError,
            match="Insufficient stock for product Product 1",
        ):
            await order_service.create(mock_session, order_data)

        mock_order_repository.create.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_order_invalid_product(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
        mock_product_repository,
    ):
        """Тест создания заказа с несуществующим продуктом."""
        mock_user = Mock(spec=User)
        mock_user.id = 1

        mock_address = Mock(spec=Address)
        mock_address.id = 1
        mock_address.user_id = 1

        async def mock_execute(stmt):
            result_mock = Mock()
            if "users" in str(stmt).lower() or "User" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_user
            elif "addresses" in str(stmt).lower() or "Address" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_address
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_product_repository.get_by_id.return_value = None  # Продукт не найден

        order_data = OrderCreate(
            user_id=1,
            delivery_address_id=1,
            items=[OrderItemCreate(product_id=999, quantity=1)],
        )

        with pytest.raises(ValueError, match="Product with ID 999 not found"):
            await order_service.create(mock_session, order_data)

        mock_order_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_order_invalid_user(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
        mock_product_repository,
    ):
        """Тест создания заказа с несуществующим пользователем."""
        async def mock_execute(stmt):
            result_mock = Mock()
            if "users" in str(stmt).lower() or "User" in str(stmt):
                result_mock.scalar_one_or_none.return_value = None  # Пользователь не найден
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        order_data = OrderCreate(
            user_id=999,
            delivery_address_id=1,
            items=[OrderItemCreate(product_id=1, quantity=1)],
        )

        with pytest.raises(ValueError, match="User with ID 999 not found"):
            await order_service.create(mock_session, order_data)

        mock_order_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_order_invalid_address(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
        mock_product_repository,
    ):
        """Тест создания заказа с несуществующим адресом."""
        mock_user = Mock(spec=User)
        mock_user.id = 1

        async def mock_execute(stmt):
            result_mock = Mock()
            if "users" in str(stmt).lower() or "User" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_user
            elif "addresses" in str(stmt).lower() or "Address" in str(stmt):
                result_mock.scalar_one_or_none.return_value = None  # Адрес не найден
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        order_data = OrderCreate(
            user_id=1,
            delivery_address_id=999,
            items=[OrderItemCreate(product_id=1, quantity=1)],
        )

        with pytest.raises(ValueError, match="Address with ID 999 not found"):
            await order_service.create(mock_session, order_data)

        mock_order_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_order_address_belongs_to_different_user(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
        mock_product_repository,
    ):
        """Тест создания заказа, когда адрес принадлежит другому пользователю."""
        mock_user = Mock(spec=User)
        mock_user.id = 1

        mock_address = Mock(spec=Address)
        mock_address.id = 1
        mock_address.user_id = 2  # Адрес принадлежит другому пользователю

        async def mock_execute(stmt):
            result_mock = Mock()
            if "users" in str(stmt).lower() or "User" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_user
            elif "addresses" in str(stmt).lower() or "Address" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_address
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        order_data = OrderCreate(
            user_id=1,
            delivery_address_id=1,
            items=[OrderItemCreate(product_id=1, quantity=1)],
        )

        with pytest.raises(ValueError, match="Delivery address does not belong to the user"):
            await order_service.create(mock_session, order_data)

        mock_order_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_calculate_total_price(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
        mock_product_repository,
    ):
        """Тест расчета общей стоимости заказа."""
        mock_user = Mock(spec=User)
        mock_user.id = 1

        mock_address = Mock(spec=Address)
        mock_address.id = 1
        mock_address.user_id = 1

        # Продукты с разными ценами
        mock_product1 = Mock(spec=Product)
        mock_product1.id = 1
        mock_product1.price = 100.0
        mock_product1.stock_quantity = 10

        mock_product2 = Mock(spec=Product)
        mock_product2.id = 2
        mock_product2.price = 50.0
        mock_product2.stock_quantity = 5

        mock_product3 = Mock(spec=Product)
        mock_product3.id = 3
        mock_product3.price = 25.0
        mock_product3.stock_quantity = 20

        mock_order = Mock(spec=Order)
        mock_order.id = 1
        mock_order.items = []

        async def mock_execute(stmt):
            result_mock = Mock()
            if "users" in str(stmt).lower() or "User" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_user
            elif "addresses" in str(stmt).lower() or "Address" in str(stmt):
                result_mock.scalar_one_or_none.return_value = mock_address
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_product_repository.get_by_id.side_effect = [
            mock_product1,
            mock_product2,
            mock_product3,
        ]
        mock_order_repository.create.return_value = mock_order

        order_data = OrderCreate(
            user_id=1,
            delivery_address_id=1,
            items=[
                OrderItemCreate(product_id=1, quantity=2),  # 100 * 2 = 200
                OrderItemCreate(product_id=2, quantity=3),  # 50 * 3 = 150
                OrderItemCreate(product_id=3, quantity=4),  # 25 * 4 = 100
            ],
        )

        result = await order_service.create(mock_session, order_data)

        # Проверяем, что total_price был рассчитан правильно: 200 + 150 + 100 = 450
        call_args = mock_order_repository.create.call_args
        assert call_args[0][2] == 450.0  # total_price

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
    ):
        """Тест успешного получения заказа по ID."""
        mock_order = Mock(spec=Order)
        mock_order.id = 1
        mock_order.user_id = 1

        mock_order_repository.get_by_id.return_value = mock_order

        result = await order_service.get_by_id(mock_session, 1)

        assert result is not None
        assert result.id == 1
        mock_order_repository.get_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_update_order_success(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
    ):
        """Тест успешного обновления заказа."""
        existing_order = Mock(spec=Order)
        existing_order.id = 1
        existing_order.status = "pending"

        updated_order = Mock(spec=Order)
        updated_order.id = 1
        updated_order.status = "completed"

        update_data = OrderUpdate(status="completed")

        mock_order_repository.get_by_id.return_value = existing_order
        mock_order_repository.update.return_value = updated_order

        result = await order_service.update(mock_session, 1, update_data)

        assert result.status == "completed"
        mock_order_repository.update.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_order_not_found(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
    ):
        """Тест обновления несуществующего заказа."""
        update_data = OrderUpdate(status="completed")

        mock_order_repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Order with ID 999 not found"):
            await order_service.update(mock_session, 999, update_data)

        mock_order_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_order_success(
        self,
        order_service: OrderService,
        mock_session,
        mock_order_repository,
    ):
        """Тест успешного удаления заказа."""
        mock_order_repository.delete.return_value = None

        await order_service.delete(mock_session, 1)

        mock_order_repository.delete.assert_called_once_with(mock_session, 1)
        mock_session.commit.assert_called_once()

