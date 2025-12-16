"""Схемы Pydantic для валидации данных."""

from app.schemas.order_schema import (
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderUpdate,
    OrderUpdateMessage,
)
from app.schemas.product_schema import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProductUpdateMessage,
)
from app.schemas.report_schema import (
    ReportCreate,
    ReportDateRequest,
    ReportResponse,
)
from app.schemas.user_schema import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "ProductCreate",
    "ProductResponse",
    "ProductUpdate",
    "ProductUpdateMessage",
    "OrderCreate",
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderResponse",
    "OrderListResponse",
    "OrderUpdate",
    "OrderUpdateMessage",
    "ReportCreate",
    "ReportDateRequest",
    "ReportResponse",
]
