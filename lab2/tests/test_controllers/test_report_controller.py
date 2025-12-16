"""Тесты для API эндпоинтов отчетов."""

import pytest
from datetime import date
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from app.models import Report, Order, User, Address, Product
from app.repositories.report_repository import ReportRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate, OrderItemCreate
from app.schemas.product_schema import ProductCreate
from app.schemas.user_schema import UserCreate


class TestReportController:
    """Тесты для API эндпоинтов отчетов."""

    @pytest.fixture
    async def test_user(
        self, controller_session, user_repository: UserRepository
    ) -> User:
        """Создает тестового пользователя."""
        user_data = UserCreate(
            email="report_test@example.com",
            username="report_test_user",
        )
        user = await user_repository.create(controller_session, user_data)
        await controller_session.commit()
        return user

    @pytest.fixture
    async def test_address(
        self, controller_session, test_user: User
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
        controller_session.add(address)
        await controller_session.commit()
        return address

    @pytest.fixture
    async def test_product(
        self, controller_session, product_repository: ProductRepository
    ) -> Product:
        """Создает тестовый продукт."""
        product_data = ProductCreate(
            name="Test Product",
            price=99.99,
            stock_quantity=100,
        )
        product = await product_repository.create(controller_session, product_data)
        await controller_session.commit()
        return product

    @pytest.fixture
    async def test_order(
        self,
        controller_session,
        order_repository: OrderRepository,
        test_user: User,
        test_address: Address,
        test_product: Product,
    ) -> Order:
        """Создает тестовый заказ."""
        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=[OrderItemCreate(product_id=test_product.id, quantity=3)],
            status="pending",
        )
        order = await order_repository.create(controller_session, order_data, total_price=299.97)
        await controller_session.commit()
        return order

    @pytest.fixture
    async def test_report(
        self,
        controller_session,
        report_repository: ReportRepository,
        test_order: Order,
    ) -> Report:
        """Создает тестовый отчет."""
        report_date = date.today()
        report = await report_repository.create_report(
            session=controller_session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=3,
        )
        await controller_session.commit()
        return report

    @pytest.mark.asyncio
    async def test_get_report_without_date(
        self,
        client: TestClient,
        controller_session,
        test_report: Report,
    ):
        """Тест GET /report без параметра date (должен вернуть отчет за сегодня)."""
        response = client.get("/report")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Проверяем, что есть отчет за сегодня
        today_reports = [r for r in data if r["report_at"] == date.today().isoformat()]
        assert len(today_reports) > 0

    @pytest.mark.asyncio
    async def test_get_report_with_date(
        self,
        client: TestClient,
        controller_session,
        report_repository: ReportRepository,
        test_order: Order,
    ):
        """Тест GET /report с параметром date."""
        # Создаем отчет за конкретную дату
        report_date = date(2024, 1, 15)
        report = await report_repository.create_report(
            session=controller_session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=5,
        )
        await controller_session.commit()

        # Запрашиваем отчет за эту дату
        response = client.get(f"/report?date={report_date.isoformat()}")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == report.id
        assert data[0]["report_at"] == report_date.isoformat()
        assert data[0]["order_id"] == test_order.id
        assert data[0]["count_product"] == 5

    @pytest.mark.asyncio
    async def test_get_report_empty_date(
        self,
        client: TestClient,
    ):
        """Тест GET /report с датой, для которой нет отчетов."""
        report_date = date(2020, 1, 1)
        response = client.get(f"/report?date={report_date.isoformat()}")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_report_multiple_reports(
        self,
        client: TestClient,
        controller_session,
        report_repository: ReportRepository,
        test_order: Order,
    ):
        """Тест GET /report с несколькими отчетами за одну дату."""
        report_date = date(2024, 1, 20)

        # Создаем несколько отчетов
        report1 = await report_repository.create_report(
            session=controller_session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=2,
        )
        report2 = await report_repository.create_report(
            session=controller_session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=4,
        )
        await controller_session.commit()

        response = client.get(f"/report?date={report_date.isoformat()}")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        report_ids = [r["id"] for r in data]
        assert report1.id in report_ids
        assert report2.id in report_ids

