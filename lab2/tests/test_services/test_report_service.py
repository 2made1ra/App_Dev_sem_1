"""Тесты для сервиса отчетов."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderItem
from app.services.report_service import ReportService
from app.repositories.order_repository import OrderRepository
from app.repositories.report_repository import ReportRepository


class TestReportService:
    """Тесты для сервиса отчетов с моками."""

    @pytest.fixture
    def mock_order_repository(self):
        """Создает мок репозитория заказов."""
        return AsyncMock(spec=OrderRepository)

    @pytest.fixture
    def mock_report_repository(self):
        """Создает мок репозитория отчетов."""
        return AsyncMock(spec=ReportRepository)

    @pytest.fixture
    def mock_session(self):
        """Создает мок сессии БД."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def report_service(self, mock_order_repository, mock_report_repository):
        """Создает экземпляр сервиса с моками репозиториев."""
        return ReportService(mock_order_repository, mock_report_repository)

    @pytest.mark.asyncio
    async def test_generate_report_success(
        self,
        report_service: ReportService,
        mock_session,
        mock_order_repository,
        mock_report_repository,
    ):
        """Тест успешного формирования отчета."""
        report_date = date(2024, 1, 15)

        # Создаем моки заказов с элементами
        mock_item1 = Mock(spec=OrderItem)
        mock_item1.quantity = 2

        mock_item2 = Mock(spec=OrderItem)
        mock_item2.quantity = 3

        mock_order1 = Mock(spec=Order)
        mock_order1.id = 1
        mock_order1.items = [mock_item1]

        mock_order2 = Mock(spec=Order)
        mock_order2.id = 2
        mock_order2.items = [mock_item2]

        # Настраиваем моки
        mock_order_repository.get_orders_by_date.return_value = [
            mock_order1,
            mock_order2,
        ]

        mock_report1 = Mock()
        mock_report1.id = 1
        mock_report1.report_at = report_date
        mock_report1.order_id = 1
        mock_report1.count_product = 2

        mock_report2 = Mock()
        mock_report2.id = 2
        mock_report2.report_at = report_date
        mock_report2.order_id = 2
        mock_report2.count_product = 3

        mock_report_repository.create_report.side_effect = [mock_report1, mock_report2]

        # Выполняем тест
        reports = await report_service.generate_report(mock_session, report_date)

        # Проверяем результаты
        assert len(reports) == 2
        assert reports[0].id == 1
        assert reports[0].count_product == 2
        assert reports[1].id == 2
        assert reports[1].count_product == 3

        # Проверяем вызовы
        mock_order_repository.get_orders_by_date.assert_called_once_with(
            mock_session, report_date
        )
        assert mock_report_repository.create_report.call_count == 2
        mock_session.commit.assert_called_once()
        assert mock_session.refresh.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_report_no_orders(
        self,
        report_service: ReportService,
        mock_session,
        mock_order_repository,
        mock_report_repository,
    ):
        """Тест формирования отчета, когда нет заказов."""
        report_date = date(2024, 1, 15)

        mock_order_repository.get_orders_by_date.return_value = []

        reports = await report_service.generate_report(mock_session, report_date)

        assert len(reports) == 0
        mock_order_repository.get_orders_by_date.assert_called_once_with(
            mock_session, report_date
        )
        mock_report_repository.create_report.assert_not_called()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_report_by_date(
        self,
        report_service: ReportService,
        mock_session,
        mock_report_repository,
    ):
        """Тест получения отчетов по дате."""
        report_date = date(2024, 1, 15)

        mock_report1 = Mock()
        mock_report1.id = 1
        mock_report1.report_at = report_date

        mock_report2 = Mock()
        mock_report2.id = 2
        mock_report2.report_at = report_date

        mock_report_repository.get_reports_by_date.return_value = [
            mock_report1,
            mock_report2,
        ]

        reports = await report_service.get_report_by_date(mock_session, report_date)

        assert len(reports) == 2
        mock_report_repository.get_reports_by_date.assert_called_once_with(
            mock_session, report_date
        )

