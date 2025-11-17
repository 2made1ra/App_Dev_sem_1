"""Исключения для обработки ошибок API."""

from litestar.exceptions import HTTPException


class NotFoundException(HTTPException):
    """Исключение для случая, когда ресурс не найден."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)

