import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from litestar.testing import TestClient

from app.models import Product
from app.schemas.product_schema import ProductCreate
from app.repositories.product_repository import ProductRepository


class TestProductController:
    """Тесты для API эндпоинтов продуктов."""

    @pytest.mark.asyncio
    async def test_get_product_by_id(
        self, client: TestClient, controller_session, product_repository: ProductRepository
    ):
        """Тест GET /products/{product_id} - получение продукта по ID."""
        # Создаем продукт в БД
        product_data = ProductCreate(
            name="Test Product",
            description="Test description",
            price=99.99,
            stock_quantity=10,
        )
        created_product = await product_repository.create(controller_session, product_data)
        await controller_session.commit()

        # Делаем запрос к API
        response = client.get(f"/products/{created_product.id}")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == created_product.id
        assert data["name"] == "Test Product"
        assert data["price"] == 99.99
        assert data["stock_quantity"] == 10

    @pytest.mark.asyncio
    async def test_get_product_by_id_not_found(self, client: TestClient):
        """Тест GET /products/{product_id} - несуществующий продукт."""
        response = client.get("/products/99999")

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_all_products(
        self, client: TestClient, controller_session, product_repository: ProductRepository
    ):
        """Тест GET /products - получение списка продуктов."""
        # Создаем несколько продуктов
        for i in range(3):
            product_data = ProductCreate(
                name=f"Product {i}",
                price=10.0 * (i + 1),
                stock_quantity=10,
            )
            await product_repository.create(controller_session, product_data)
        await controller_session.commit()

        response = client.get("/products")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert len(data["products"]) >= 3
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_get_products_pagination(
        self, client: TestClient, controller_session, product_repository: ProductRepository
    ):
        """Тест GET /products - проверка пагинации."""
        # Создаем 5 продуктов
        for i in range(5):
            product_data = ProductCreate(
                name=f"Paginated Product {i}",
                price=10.0 * (i + 1),
                stock_quantity=10,
            )
            await product_repository.create(controller_session, product_data)
        await controller_session.commit()

        # Первая страница (2 записи)
        response = client.get("/products?count=2&page=1")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["products"]) == 2
        assert data["total"] >= 5

        # Вторая страница (2 записи)
        response = client.get("/products?count=2&page=2")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["products"]) == 2

    @pytest.mark.asyncio
    async def test_get_products_with_filters(
        self, client: TestClient, controller_session, product_repository: ProductRepository
    ):
        """Тест GET /products - фильтрация."""
        # Создаем продукты с разными ценами
        product1 = ProductCreate(name="Cheap Product", price=10.0, stock_quantity=10)
        product2 = ProductCreate(name="Expensive Product", price=100.0, stock_quantity=5)
        product3 = ProductCreate(name="Medium Product", price=50.0, stock_quantity=15)

        await product_repository.create(controller_session, product1)
        await product_repository.create(controller_session, product2)
        await product_repository.create(controller_session, product3)
        await controller_session.commit()

        # Фильтр по названию
        response = client.get("/products?name=Cheap")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["products"]) >= 1
        assert any(p["name"] == "Cheap Product" for p in data["products"])

        # Фильтр по минимальной цене
        response = client.get("/products?min_price=50.0")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert all(p["price"] >= 50.0 for p in data["products"])

        # Фильтр по максимальной цене
        response = client.get("/products?max_price=50.0")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert all(p["price"] <= 50.0 for p in data["products"])

    @pytest.mark.asyncio
    async def test_create_product(self, client: TestClient):
        """Тест POST /products - создание продукта."""
        product_data = {
            "name": "New Product",
            "description": "New product description",
            "price": 50.0,
            "stock_quantity": 20,
        }

        response = client.post("/products", json=product_data)

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["name"] == product_data["name"]
        assert data["price"] == product_data["price"]
        assert data["stock_quantity"] == product_data["stock_quantity"]
        assert "id" in data
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_create_product_invalid_price(self, client: TestClient):
        """Тест POST /products - создание продукта с невалидной ценой."""
        product_data = {
            "name": "Invalid Product",
            "price": 0.0,  # Невалидная цена
            "stock_quantity": 10,
        }

        response = client.post("/products", json=product_data)

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        # Pydantic валидирует на уровне схемы, поэтому ошибка будет о валидации
        detail_lower = data.get("detail", "").lower()
        assert "price" in detail_lower or "greater than" in detail_lower or "validation" in detail_lower

    @pytest.mark.asyncio
    async def test_update_product(
        self, client: TestClient, controller_session, product_repository: ProductRepository
    ):
        """Тест PUT /products/{product_id} - обновление продукта."""
        # Создаем продукт
        product_data = ProductCreate(
            name="Original Product",
            price=100.0,
            stock_quantity=20,
        )
        created_product = await product_repository.create(controller_session, product_data)
        await controller_session.commit()

        # Обновляем продукт
        update_data = {
            "name": "Updated Product",
            "price": 150.0,
        }

        response = client.put(f"/products/{created_product.id}", json=update_data)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == created_product.id
        assert data["name"] == "Updated Product"
        assert data["price"] == 150.0
        assert data["stock_quantity"] == 20  # Не изменилось

    @pytest.mark.asyncio
    async def test_update_product_not_found(self, client: TestClient):
        """Тест PUT /products/{product_id} - обновление несуществующего продукта."""
        update_data = {"name": "New Name"}

        response = client.put("/products/99999", json=update_data)

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_product(
        self, client: TestClient, controller_session, product_repository: ProductRepository
    ):
        """Тест DELETE /products/{product_id} - удаление продукта."""
        # Создаем продукт
        product_data = ProductCreate(
            name="Product to Delete",
            price=25.0,
            stock_quantity=5,
        )
        created_product = await product_repository.create(controller_session, product_data)
        await controller_session.commit()

        # Удаляем продукт
        response = client.delete(f"/products/{created_product.id}")

        assert response.status_code == HTTP_204_NO_CONTENT

        # Проверяем, что продукт удален
        get_response = client.get(f"/products/{created_product.id}")
        assert get_response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_product_not_found(self, client: TestClient):
        """Тест DELETE /products/{product_id} - удаление несуществующего продукта."""
        response = client.delete("/products/99999")

        assert response.status_code == HTTP_404_NOT_FOUND

