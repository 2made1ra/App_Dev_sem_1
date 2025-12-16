"""Контроллер для управления отчетами."""

from datetime import date

from litestar import Controller, get
from litestar.exceptions import ValidationException
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.report_schema import ReportResponse
from app.services.report_service import ReportService


class ReportController(Controller):
    """Контроллер для управления отчетами."""

    path = "/report"

    @get("/")
    async def get_report(
        self,
        report_service: ReportService,
        db_session: AsyncSession,
        report_date: date | None = Parameter(
            default=None,
            description="Дата для получения отчета (по умолчанию текущая дата)",
        ),
    ) -> list[ReportResponse]:
        """
        Получить отчеты за указанную дату.

        Args:
            report_service: Сервис для работы с отчетами
            db_session: Сессия базы данных
            report_date: Дата для получения отчета (опционально, по умолчанию текущая дата)

        Returns:
            list[ReportResponse]: Список отчетов за указанную дату
        """
        # Если дата не указана, используем сегодняшнюю
        if report_date is None:
            report_date = date.today()

        reports = await report_service.get_report_by_date(db_session, report_date)
        return [ReportResponse.model_validate(report) for report in reports]
