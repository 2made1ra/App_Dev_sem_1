from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    """Схема для создания элемента заказа."""

    product_id: int = Field(..., gt=0, description="ID продукта")
    quantity: int = Field(..., gt=0, description="Количество товара")


class OrderItemResponse(BaseModel):
    """Схема для ответа API с данными элемента заказа."""

    id: int = Field(..., gt=0, description="Уникальный идентификатор элемента заказа")
    product_id: int = Field(..., gt=0, description="ID продукта")
    quantity: int = Field(..., description="Количество товара")
    price_at_order: float = Field(..., description="Цена на момент заказа")
    created_at: datetime = Field(..., description="Дата и время создания")

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Схема для создания нового заказа."""

    user_id: int = Field(..., gt=0, description="ID пользователя")
    delivery_address_id: int = Field(..., gt=0, description="ID адреса доставки")
    items: list[OrderItemCreate] = Field(
        ..., min_length=1, description="Список товаров в заказе"
    )
    status: str | None = Field(
        None, description="Статус заказа (по умолчанию 'pending')"
    )


class OrderUpdate(BaseModel):
    """Схема для обновления заказа. Все поля опциональные."""

    status: str | None = Field(None, description="Статус заказа")


class OrderUpdateMessage(BaseModel):
    """Схема для сообщения обновления заказа через RabbitMQ."""

    order_id: int = Field(..., gt=0, description="ID заказа для обновления")
    order_data: OrderUpdate = Field(..., description="Данные для обновления заказа")


class OrderResponse(BaseModel):
    """Схема для ответа API с данными заказа."""

    id: int = Field(..., gt=0, description="Уникальный идентификатор заказа")
    user_id: int = Field(..., gt=0, description="ID пользователя")
    delivery_address_id: int = Field(..., gt=0, description="ID адреса доставки")
    total_price: float = Field(..., description="Общая стоимость заказа")
    status: str = Field(..., description="Статус заказа")
    order_date: datetime = Field(..., description="Дата заказа")
    created_at: datetime = Field(..., description="Дата и время создания")
    updated_at: datetime | None = Field(
        None, description="Дата и время последнего обновления"
    )
    items: list[OrderItemResponse] = Field(..., description="Список товаров в заказе")

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    """Схема для ответа API со списком заказов и общим количеством."""

    orders: list[OrderResponse] = Field(..., description="Список заказов")
    total: int = Field(..., ge=0, description="Общее количество заказов в базе данных")
