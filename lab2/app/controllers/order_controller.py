from litestar import Controller, get, post, put, delete
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.exceptions import NotFoundException
from app.models import Order
from app.schemas.order_schema import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderListResponse,
)
from app.services.order_service import OrderService


class OrderController(Controller):
    """Контроллер для управления заказами."""

    path = "/orders"

    @get("/{order_id:int}")
    async def get_order_by_id(
        self,
        order_service: OrderService,
        db_session: AsyncSession,
        order_id: int = Parameter(gt=0, description="ID заказа"),
    ) -> OrderResponse:
        """
        Получить заказ по ID.
        Args:
            order_service: Сервис для работы с заказами
            db_session: Сессия базы данных
            order_id: ID заказа (int)
            
        Returns:
            OrderResponse: Данные заказа с элементами
            
        Raises:
            NotFoundException: Если заказ не найден
        """
        order = await order_service.get_by_id(db_session, order_id)
        if not order:
            raise NotFoundException(
                detail=f"Order with ID {order_id} not found"
            )
        # Убеждаемся, что items загружены перед валидацией Pydantic
        stmt = (
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items))
        )
        result = await db_session.execute(stmt)
        order_with_items = result.scalar_one()
        return OrderResponse.model_validate(order_with_items)

    @get()
    async def get_all_orders(
        self,
        order_service: OrderService,
        db_session: AsyncSession,
        count: int = Parameter(
            default=10, ge=1, le=100, description="Количество записей на странице"
        ),
        page: int = Parameter(
            default=1, ge=1, description="Номер страницы (начинается с 1)"
        ),
        user_id: int | None = Parameter(
            default=None, gt=0, description="Фильтр по ID пользователя"
        ),
        status: str | None = Parameter(
            default=None, description="Фильтр по статусу заказа"
        ),
    ) -> OrderListResponse:
        """
        Получить список заказов с пагинацией и фильтрацией.
        Args:
            order_service: Сервис для работы с заказами
            db_session: Сессия базы данных
            count: Количество записей на странице (1-100)
            page: Номер страницы (начинается с 1)
            user_id: Фильтр по ID пользователя
            status: Фильтр по статусу заказа
            
        Returns:
            OrderListResponse: Список заказов и общее количество
        """
        filters = {}
        if user_id is not None:
            filters["user_id"] = user_id
        if status:
            filters["status"] = status

        orders = await order_service.get_by_filter(db_session, count, page, **filters)
        total = await order_service.count(db_session, **filters)
        
        return OrderListResponse(
            orders=[OrderResponse.model_validate(order) for order in orders],
            total=total,
        )

    @post()
    async def create_order(
        self,
        order_service: OrderService,
        db_session: AsyncSession,
        data: OrderCreate,
    ) -> OrderResponse:
        """
        Создать новый заказ с несколькими продуктами.
        Args:
            order_service: Сервис для работы с заказами
            db_session: Сессия базы данных
            data: Данные для создания заказа
            
        Returns:
            OrderResponse: Созданный заказ
            
        Raises:
            HTTPException: Если данные невалидны или недостаточно товара на складе
        """
        try:
            order = await order_service.create(db_session, data)
            # Убеждаемся, что items загружены перед валидацией Pydantic
            stmt = (
                select(Order)
                .where(Order.id == order.id)
                .options(selectinload(Order.items))
            )
            result = await db_session.execute(stmt)
            order_with_items = result.scalar_one()
            return OrderResponse.model_validate(order_with_items)
        except ValueError as e:
            from litestar.exceptions import HTTPException
            raise HTTPException(status_code=400, detail=str(e))

    @put("/{order_id:int}")
    async def update_order(
        self,
        order_service: OrderService,
        db_session: AsyncSession,
        data: OrderUpdate,
        order_id: int = Parameter(gt=0, description="ID заказа"),
    ) -> OrderResponse:
        """
        Обновить заказ (в основном статус).
        Args:
            order_service: Сервис для работы с заказами
            db_session: Сессия базы данных
            order_id: ID заказа (int)
            data: Данные для обновления
            
        Returns:
            OrderResponse: Обновленный заказ
            
        Raises:
            NotFoundException: Если заказ не найден
            HTTPException: Если данные невалидны
        """
        try:
            order = await order_service.update(db_session, order_id, data)
            # Убеждаемся, что items загружены перед валидацией Pydantic
            stmt = (
                select(Order)
                .where(Order.id == order.id)
                .options(selectinload(Order.items))
            )
            result = await db_session.execute(stmt)
            order_with_items = result.scalar_one()
            return OrderResponse.model_validate(order_with_items)
        except ValueError as e:
            error_message = str(e)
            if "not found" in error_message.lower():
                raise NotFoundException(detail=error_message)
            from litestar.exceptions import HTTPException
            raise HTTPException(status_code=400, detail=error_message)

    @delete("/{order_id:int}")
    async def delete_order(
        self,
        order_service: OrderService,
        db_session: AsyncSession,
        order_id: int = Parameter(gt=0, description="ID заказа"),
    ) -> None:
        """
        Удалить заказ.
        Args:
            order_service: Сервис для работы с заказами
            db_session: Сессия базы данных
            order_id: ID заказа (int)
            
        Raises:
            NotFoundException: Если заказ не найден
        """
        try:
            await order_service.delete(db_session, order_id)
        except ValueError as e:
            raise NotFoundException(detail=str(e))

