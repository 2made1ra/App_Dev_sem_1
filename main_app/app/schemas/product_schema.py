from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """Схема для создания нового продукта."""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Название продукта"
    )
    description: str | None = Field(
        None, max_length=1000, description="Описание продукта"
    )
    price: float = Field(..., gt=0, description="Цена продукта")
    stock_quantity: int = Field(..., ge=0, description="Количество товара на складе")


class ProductUpdate(BaseModel):
    """Схема для обновления продукта. Все поля опциональные."""

    name: str | None = Field(
        None, min_length=1, max_length=200, description="Название продукта"
    )
    description: str | None = Field(
        None, max_length=1000, description="Описание продукта"
    )
    price: float | None = Field(None, gt=0, description="Цена продукта")
    stock_quantity: int | None = Field(
        None, ge=0, description="Количество товара на складе"
    )


class ProductUpdateMessage(BaseModel):
    """Схема для сообщения обновления продукта через RabbitMQ."""

    product_id: int = Field(..., gt=0, description="ID продукта для обновления")
    product_data: ProductUpdate = Field(
        ..., description="Данные для обновления продукта"
    )


class ProductResponse(BaseModel):
    """Схема для ответа API с данными продукта."""

    id: int = Field(..., gt=0, description="Уникальный идентификатор продукта")
    name: str = Field(..., description="Название продукта")
    description: str | None = Field(None, description="Описание продукта")
    price: float = Field(..., description="Цена продукта")
    stock_quantity: int = Field(..., description="Количество товара на складе")
    created_at: datetime = Field(..., description="Дата и время создания")
    updated_at: datetime | None = Field(
        None, description="Дата и время последнего обновления"
    )

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    """Схема для ответа API со списком продуктов и общим количеством."""

    products: list[ProductResponse] = Field(..., description="Список продуктов")
    total: int = Field(
        ..., ge=0, description="Общее количество продуктов в базе данных"
    )
