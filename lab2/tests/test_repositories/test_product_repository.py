import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schema import ProductCreate, ProductUpdate


class TestProductRepository:
    """Тесты для репозитория продуктов."""

    @pytest.mark.asyncio
    async def test_create_product(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест создания продукта в репозитории."""
        product_data = ProductCreate(
            name="Test Product",
            description="Test description",
            price=99.99,
            stock_quantity=10,
        )

        product = await product_repository.create(session, product_data)
        await session.commit()

        assert product.id is not None
        assert product.name == "Test Product"
        assert product.description == "Test description"
        assert product.price == 99.99
        assert product.stock_quantity == 10

    @pytest.mark.asyncio
    async def test_get_product_by_id(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест получения продукта по ID."""
        product_data = ProductCreate(
            name="Get By ID Product",
            description="Product for get_by_id test",
            price=50.0,
            stock_quantity=5,
        )
        created_product = await product_repository.create(session, product_data)
        await session.commit()

        found_product = await product_repository.get_by_id(
            session, created_product.id
        )

        assert found_product is not None
        assert found_product.id == created_product.id
        assert found_product.name == "Get By ID Product"
        assert found_product.price == 50.0

    @pytest.mark.asyncio
    async def test_get_product_by_id_not_found(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест получения несуществующего продукта по ID."""
        found_product = await product_repository.get_by_id(session, 99999)

        assert found_product is None

    @pytest.mark.asyncio
    async def test_update_product(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест обновления продукта."""
        product_data = ProductCreate(
            name="Original Product",
            description="Original description",
            price=100.0,
            stock_quantity=20,
        )
        created_product = await product_repository.create(session, product_data)
        await session.commit()

        update_data = ProductUpdate(
            name="Updated Product",
            price=150.0,
        )
        updated_product = await product_repository.update(
            session, created_product.id, update_data
        )
        await session.commit()

        assert updated_product.id == created_product.id
        assert updated_product.name == "Updated Product"
        assert updated_product.price == 150.0
        assert updated_product.description == "Original description"  # не изменилось
        assert updated_product.stock_quantity == 20  # не изменилось

    @pytest.mark.asyncio
    async def test_update_product_not_found(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест обновления несуществующего продукта."""
        update_data = ProductUpdate(name="New Name")

        with pytest.raises(ValueError, match="Product with ID 99999 not found"):
            await product_repository.update(session, 99999, update_data)

    @pytest.mark.asyncio
    async def test_delete_product(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест удаления продукта."""
        product_data = ProductCreate(
            name="Product to Delete",
            description="Will be deleted",
            price=25.0,
            stock_quantity=5,
        )
        created_product = await product_repository.create(session, product_data)
        await session.commit()

        await product_repository.delete(session, created_product.id)
        await session.commit()

        deleted_product = await product_repository.get_by_id(
            session, created_product.id
        )
        assert deleted_product is None

    @pytest.mark.asyncio
    async def test_delete_product_not_found(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест удаления несуществующего продукта."""
        with pytest.raises(
            ValueError, match="Product with ID 99999 not found"
        ):
            await product_repository.delete(session, 99999)

    @pytest.mark.asyncio
    async def test_get_all_products(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест получения списка продуктов."""
        # Создаем несколько продуктов
        for i in range(5):
            product_data = ProductCreate(
                name=f"Product {i}",
                description=f"Description {i}",
                price=10.0 * (i + 1),
                stock_quantity=i + 1,
            )
            await product_repository.create(session, product_data)
        await session.commit()

        products = await product_repository.get_by_filter(session, count=10, page=1)
        total = await product_repository.count(session)

        assert len(products) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_products_with_pagination(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест получения списка продуктов с пагинацией."""
        # Создаем 10 продуктов
        for i in range(10):
            product_data = ProductCreate(
                name=f"Paginated Product {i}",
                price=10.0 * (i + 1),
                stock_quantity=10,
            )
            await product_repository.create(session, product_data)
        await session.commit()

        # Первая страница (5 записей)
        page1 = await product_repository.get_by_filter(session, count=5, page=1)
        assert len(page1) == 5

        # Вторая страница (5 записей)
        page2 = await product_repository.get_by_filter(session, count=5, page=2)
        assert len(page2) == 5

    @pytest.mark.asyncio
    async def test_get_products_with_filters(
        self, session: AsyncSession, product_repository: ProductRepository
    ):
        """Тест получения продуктов с фильтрацией."""
        # Создаем продукты с разными ценами
        product1 = ProductCreate(
            name="Cheap Product",
            price=10.0,
            stock_quantity=10,
        )
        product2 = ProductCreate(
            name="Expensive Product",
            price=100.0,
            stock_quantity=5,
        )
        product3 = ProductCreate(
            name="Medium Product",
            price=50.0,
            stock_quantity=15,
        )
        await product_repository.create(session, product1)
        await product_repository.create(session, product2)
        await product_repository.create(session, product3)
        await session.commit()

        # Фильтр по названию
        products = await product_repository.get_by_filter(
            session, count=10, page=1, name="Cheap"
        )
        assert len(products) == 1
        assert products[0].name == "Cheap Product"

        # Фильтр по минимальной цене
        products = await product_repository.get_by_filter(
            session, count=10, page=1, min_price=50.0
        )
        assert len(products) == 2  # Expensive и Medium

        # Фильтр по максимальной цене
        products = await product_repository.get_by_filter(
            session, count=10, page=1, max_price=50.0
        )
        assert len(products) == 2  # Cheap и Medium

        # Фильтр по диапазону цен
        products = await product_repository.get_by_filter(
            session, count=10, page=1, min_price=20.0, max_price=80.0
        )
        assert len(products) == 1  # Только Medium

