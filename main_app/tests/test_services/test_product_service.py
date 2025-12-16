import pytest
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.services.product_service import ProductService
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import ProductCreate, ProductUpdate


class TestProductService:
    """Тесты для сервиса продуктов с моками."""

    @pytest.fixture
    def mock_product_repository(self):
        """Создает мок репозитория продуктов."""
        return AsyncMock(spec=ProductRepository)

    @pytest.fixture
    def mock_session(self):
        """Создает мок сессии БД."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def product_service(self, mock_product_repository):
        """Создает экземпляр сервиса с моком репозитория."""
        return ProductService(mock_product_repository)

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест успешного получения продукта по ID."""
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.name = "Test Product"
        mock_product.price = 99.99

        mock_product_repository.get_by_id.return_value = mock_product

        result = await product_service.get_by_id(mock_session, 1)

        assert result is not None
        assert result.id == 1
        assert result.name == "Test Product"
        mock_product_repository.get_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_create_product_success(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест успешного создания продукта."""
        product_data = ProductCreate(
            name="New Product",
            description="New description",
            price=50.0,
            stock_quantity=10,
        )

        mock_product = Mock(spec=Product)
        mock_product.id = 1
        mock_product.name = product_data.name
        mock_product.price = product_data.price
        mock_product.stock_quantity = product_data.stock_quantity

        mock_product_repository.create.return_value = mock_product

        result = await product_service.create(mock_session, product_data)

        assert result is not None
        assert result.id == 1
        assert result.name == product_data.name
        assert result.price == product_data.price
        mock_product_repository.create.assert_called_once_with(mock_session, product_data)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_invalid_price(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест создания продукта с невалидной ценой (<= 0)."""
        product_data = ProductCreate.model_construct(
            name="Invalid Product",
            price=0.0,
            stock_quantity=10,
        )

        with pytest.raises(ValueError, match="Price must be greater than 0"):
            await product_service.create(mock_session, product_data)

        mock_product_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_product_negative_stock(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест создания продукта с отрицательным количеством на складе."""
        product_data = ProductCreate.model_construct(
            name="Invalid Product",
            price=10.0,
            stock_quantity=-1,
        )

        with pytest.raises(ValueError, match="Stock quantity cannot be negative"):
            await product_service.create(mock_session, product_data)

        mock_product_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_product_success(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест успешного обновления продукта."""
        existing_product = Mock(spec=Product)
        existing_product.id = 1
        existing_product.name = "Old Product"
        existing_product.price = 100.0
        existing_product.stock_quantity = 20

        updated_product = Mock(spec=Product)
        updated_product.id = 1
        updated_product.name = "Updated Product"
        updated_product.price = 150.0
        updated_product.stock_quantity = 20

        update_data = ProductUpdate(name="Updated Product", price=150.0)

        mock_product_repository.get_by_id.return_value = existing_product
        mock_product_repository.update.return_value = updated_product

        result = await product_service.update(mock_session, 1, update_data)

        assert result.name == "Updated Product"
        assert result.price == 150.0
        mock_product_repository.update.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_not_found(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест обновления несуществующего продукта."""
        update_data = ProductUpdate(name="New Name")

        mock_product_repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Product with ID 999 not found"):
            await product_service.update(mock_session, 999, update_data)

        mock_product_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_product_invalid_price(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест обновления продукта с невалидной ценой."""
        existing_product = Mock(spec=Product)
        existing_product.id = 1

        update_data = ProductUpdate.model_construct(price=0.0)

        mock_product_repository.get_by_id.return_value = existing_product

        with pytest.raises(ValueError, match="Price must be greater than 0"):
            await product_service.update(mock_session, 1, update_data)

        mock_product_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_product_negative_stock(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест обновления продукта с отрицательным количеством на складе."""
        existing_product = Mock(spec=Product)
        existing_product.id = 1

        update_data = ProductUpdate.model_construct(stock_quantity=-1)

        mock_product_repository.get_by_id.return_value = existing_product

        with pytest.raises(ValueError, match="Stock quantity cannot be negative"):
            await product_service.update(mock_session, 1, update_data)

        mock_product_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_product_success(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест успешного удаления продукта."""
        mock_product_repository.delete.return_value = None

        await product_service.delete(mock_session, 1)

        mock_product_repository.delete.assert_called_once_with(mock_session, 1)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_filter(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест получения списка продуктов с фильтрацией."""
        mock_products = [
            Mock(spec=Product, id=1, name="Product 1"),
            Mock(spec=Product, id=2, name="Product 2"),
        ]

        mock_product_repository.get_by_filter.return_value = mock_products

        result = await product_service.get_by_filter(
            mock_session, count=10, page=1, name="Product"
        )

        assert len(result) == 2
        mock_product_repository.get_by_filter.assert_called_once_with(
            mock_session, 10, 1, name="Product"
        )

    @pytest.mark.asyncio
    async def test_count(
        self, product_service: ProductService, mock_session, mock_product_repository
    ):
        """Тест подсчета продуктов."""
        mock_product_repository.count.return_value = 10

        result = await product_service.count(mock_session, min_price=50.0)

        assert result == 10
        mock_product_repository.count.assert_called_once_with(
            mock_session, min_price=50.0
        )

