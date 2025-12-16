"""Тесты для репозитория отчетов."""

import pytest
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Report, Order, User, Address, Product, OrderItem
from app.repositories.report_repository import ReportRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order_schema import OrderCreate, OrderItemCreate
from app.schemas.product_schema import ProductCreate
from app.schemas.user_schema import UserCreate


class TestReportRepository:
    """Тесты для репозитория отчетов."""

    @pytest.fixture
    def report_repository(self):
        """Фикстура для репозитория отчетов."""
        return ReportRepository()

    @pytest.fixture
    async def test_user(self, session: AsyncSession, user_repository):
        """Создает тестового пользователя."""
        user_data = UserCreate(
            username="test_user",
            email="test@example.com",
            description="Test user",
        )
        user = await user_repository.create(session, user_data)
        await session.flush()
        return user

    @pytest.fixture
    async def test_address(self, session: AsyncSession, test_user):
        """Создает тестовый адрес."""
        address = Address(
            user_id=test_user.id,
            street="Test Street",
            city="Test City",
            state="Test State",
            zip_code="12345",
            country="Test Country",
            is_primary=True,
        )
        session.add(address)
        await session.flush()
        return address

    @pytest.fixture
    async def test_product(self, session: AsyncSession, product_repository):
        """Создает тестовый продукт."""
        product_data = ProductCreate(
            name="Test Product",
            description="Test description",
            price=99.99,
            stock_quantity=10,
        )
        product = await product_repository.create(session, product_data)
        await session.flush()
        return product

    @pytest.fixture
    async def test_order(
        self, session: AsyncSession, order_repository, test_user, test_address, test_product
    ):
        """Создает тестовый заказ."""
        order_data = OrderCreate(
            user_id=test_user.id,
            delivery_address_id=test_address.id,
            items=[OrderItemCreate(product_id=test_product.id, quantity=2)],
            status="pending",
        )
        order = await order_repository.create(session, order_data, total_price=199.98)
        await session.flush()
        return order

    @pytest.mark.asyncio
    async def test_create_report(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
        test_order: Order,
    ):
        """Тест создания отчета."""
        report_date = date.today()
        report = await report_repository.create_report(
            session=session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=2,
        )
        await session.flush()

        assert report.id is not None
        assert report.report_at == report_date
        assert report.order_id == test_order.id
        assert report.count_product == 2
        assert report.created_at is not None

    @pytest.mark.asyncio
    async def test_get_reports_by_date(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
        test_order: Order,
    ):
        """Тест получения отчетов по дате."""
        report_date = date.today()
        
        # Создаем несколько отчетов
        report1 = await report_repository.create_report(
            session=session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=2,
        )
        report2 = await report_repository.create_report(
            session=session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=3,
        )
        await session.flush()

        # Получаем отчеты за дату
        reports = await report_repository.get_reports_by_date(session, report_date)

        assert len(reports) == 2
        assert report1.id in [r.id for r in reports]
        assert report2.id in [r.id for r in reports]

    @pytest.mark.asyncio
    async def test_get_reports_by_date_empty(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
    ):
        """Тест получения отчетов по дате, когда отчетов нет."""
        report_date = date(2020, 1, 1)
        reports = await report_repository.get_reports_by_date(session, report_date)

        assert len(reports) == 0

    @pytest.mark.asyncio
    async def test_get_report_by_id(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
        test_order: Order,
    ):
        """Тест получения отчета по ID."""
        report_date = date.today()
        created_report = await report_repository.create_report(
            session=session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=5,
        )
        await session.flush()

        found_report = await report_repository.get_report_by_id(
            session, created_report.id
        )

        assert found_report is not None
        assert found_report.id == created_report.id
        assert found_report.order_id == test_order.id
        assert found_report.count_product == 5

    @pytest.mark.asyncio
    async def test_get_report_by_id_not_found(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
    ):
        """Тест получения несуществующего отчета."""
        report = await report_repository.get_report_by_id(session, 99999)

        assert report is None

    @pytest.mark.asyncio
    async def test_delete_report(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
        test_order: Order,
    ):
        """Тест удаления отчета."""
        report_date = date.today()
        created_report = await report_repository.create_report(
            session=session,
            report_at=report_date,
            order_id=test_order.id,
            count_product=3,
        )
        await session.flush()

        # Удаляем отчет
        await report_repository.delete_report(session, created_report.id)
        await session.flush()

        # Проверяем, что отчет удален
        found_report = await report_repository.get_report_by_id(
            session, created_report.id
        )
        assert found_report is None

    @pytest.mark.asyncio
    async def test_delete_report_not_found(
        self,
        session: AsyncSession,
        report_repository: ReportRepository,
    ):
        """Тест удаления несуществующего отчета."""
        with pytest.raises(ValueError, match="Report with ID 99999 not found"):
            await report_repository.delete_report(session, 99999)

