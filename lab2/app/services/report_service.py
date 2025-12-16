"""Сервис для бизнес-логики работы с отчетами."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.order_repository import OrderRepository
from app.repositories.report_repository import ReportRepository


class ReportService:
    """Сервис для бизнес-логики работы с отчетами."""

    def __init__(
        self,
        order_repository: OrderRepository,
        report_repository: ReportRepository,
    ):
        """
        Инициализация сервиса.

        Args:
            order_repository: Репозиторий для работы с заказами (Dependency Injection)
            report_repository: Репозиторий для работы с отчетами (Dependency Injection)
        """
        self.order_repository = order_repository
        self.report_repository = report_repository

    async def generate_report(self, session: AsyncSession, report_date: date) -> list:
        """
        Сформировать отчет за указанную дату.

        Получает все заказы за указанную дату, подсчитывает количество продукции
        в каждом заказе и создает записи отчетов.

        Args:
            session: Асинхронная сессия базы данных
            report_date: Дата для формирования отчета

        Returns:
            Список созданных отчетов
        """
        # Получаем все заказы за указанную дату
        orders = await self.order_repository.get_orders_by_date(session, report_date)

        reports = []

        # Для каждого заказа создаем отчет
        for order in orders:
            # Подсчитываем общее количество продукции в заказе
            # (сумма quantity всех элементов заказа)
            count_product = sum(item.quantity for item in order.items)

            # Создаем отчет
            report = await self.report_repository.create_report(
                session=session,
                report_at=report_date,
                order_id=order.id,
                count_product=count_product,
            )
            reports.append(report)

        # Сохраняем все отчеты в базу данных
        await session.commit()

        # Обновляем объекты отчетов после commit
        for report in reports:
            await session.refresh(report)

        return reports

    async def get_report_by_date(
        self, session: AsyncSession, report_date: date
    ) -> list:
        """
        Получить отчеты за указанную дату.

        Args:
            session: Асинхронная сессия базы данных
            report_date: Дата для получения отчетов

        Returns:
            Список отчетов за указанную дату
        """
        return await self.report_repository.get_reports_by_date(session, report_date)
