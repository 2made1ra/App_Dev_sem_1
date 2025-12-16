"""Репозитории для работы с базой данных."""

from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "ProductRepository",
    "OrderRepository",
    "ReportRepository",
]
