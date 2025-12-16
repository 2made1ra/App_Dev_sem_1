"""Схемы для работы с отчетами."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportResponse(BaseModel):
    """Схема для ответа API с данными отчета."""

    id: int = Field(..., gt=0, description="Уникальный идентификатор отчета")
    report_at: date = Field(..., description="Дата отчета")
    order_id: int = Field(..., gt=0, description="ID заказа")
    count_product: int = Field(..., ge=0, description="Количество продукции в заказе")
    created_at: datetime = Field(..., description="Дата и время создания отчета")

    model_config = ConfigDict(from_attributes=True)


class ReportDateRequest(BaseModel):
    """Схема для запроса отчета по дате."""

    report_date: date = Field(..., description="Дата для получения отчета")


class ReportCreate(BaseModel):
    """Схема для создания отчета (опционально, если нужен ручной ввод)."""

    report_at: date = Field(..., description="Дата отчета")
    order_id: int = Field(..., gt=0, description="ID заказа")
    count_product: int = Field(..., ge=0, description="Количество продукции в заказе")
