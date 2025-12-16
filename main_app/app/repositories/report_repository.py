"""Репозиторий для работы с отчетами."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Report


class ReportRepository:
    """Репозиторий для CRUD операций с отчетами."""

    async def create_report(
        self,
        session: AsyncSession,
        report_at: date,
        order_id: int,
        count_product: int,
    ) -> Report:
        """
        Создать запись отчета.

        Args:
            session: Асинхронная сессия базы данных
            report_at: Дата отчета
            order_id: ID заказа
            count_product: Количество продукции в заказе

        Returns:
            Созданный объект Report
        """
        report = Report(
            report_at=report_at,
            order_id=order_id,
            count_product=count_product,
        )
        session.add(report)
        await session.flush()
        await session.refresh(report)
        return report

    async def get_reports_by_date(
        self, session: AsyncSession, report_date: date
    ) -> list[Report]:
        """
        Получить все отчеты за указанную дату.

        Args:
            session: Асинхронная сессия базы данных
            report_date: Дата для получения отчетов

        Returns:
            Список отчетов за указанную дату
        """
        stmt = select(Report).where(Report.report_at == report_date)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_report_by_id(
        self, session: AsyncSession, report_id: int
    ) -> Report | None:
        """
        Получить отчет по ID.

        Args:
            session: Асинхронная сессия базы данных
            report_id: ID отчета

        Returns:
            Объект Report или None, если не найден
        """
        stmt = select(Report).where(Report.id == report_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_report(self, session: AsyncSession, report_id: int) -> None:
        """
        Удалить отчет.

        Args:
            session: Асинхронная сессия базы данных
            report_id: ID отчета

        Raises:
            ValueError: Если отчет не найден
        """
        report = await self.get_report_by_id(session, report_id)

        if not report:
            raise ValueError(f"Report with ID {report_id} not found")

        await session.delete(report)
        await session.flush()
