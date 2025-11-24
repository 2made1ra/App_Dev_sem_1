from litestar import Controller, get, post, put, delete
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundException
from app.schemas.product_schema import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)
from app.services.product_service import ProductService


class ProductController(Controller):
    """Контроллер для управления продуктами."""

    path = "/products"

    @get("/{product_id:int}")
    async def get_product_by_id(
        self,
        product_service: ProductService,
        db_session: AsyncSession,
        product_id: int = Parameter(gt=0, description="ID продукта"),
    ) -> ProductResponse:
        """
        Получить продукт по ID.
        Args:
            product_service: Сервис для работы с продуктами
            db_session: Сессия базы данных
            product_id: ID продукта (int)
            
        Returns:
            ProductResponse: Данные продукта
            
        Raises:
            NotFoundException: Если продукт не найден
        """
        product = await product_service.get_by_id(db_session, product_id)
        if not product:
            raise NotFoundException(
                detail=f"Product with ID {product_id} not found"
            )
        return ProductResponse.model_validate(product)

    @get()
    async def get_all_products(
        self,
        product_service: ProductService,
        db_session: AsyncSession,
        count: int = Parameter(
            default=10, ge=1, le=100, description="Количество записей на странице"
        ),
        page: int = Parameter(
            default=1, ge=1, description="Номер страницы (начинается с 1)"
        ),
        name: str | None = Parameter(
            default=None, description="Фильтр по названию продукта"
        ),
        min_price: float | None = Parameter(
            default=None, ge=0, description="Минимальная цена"
        ),
        max_price: float | None = Parameter(
            default=None, ge=0, description="Максимальная цена"
        ),
    ) -> ProductListResponse:
        """
        Получить список продуктов с пагинацией и фильтрацией.
        Args:
            product_service: Сервис для работы с продуктами
            db_session: Сессия базы данных
            count: Количество записей на странице (1-100)
            page: Номер страницы (начинается с 1)
            name: Фильтр по названию продукта
            min_price: Минимальная цена
            max_price: Максимальная цена
            
        Returns:
            ProductListResponse: Список продуктов и общее количество
        """
        filters = {}
        if name:
            filters["name"] = name
        if min_price is not None:
            filters["min_price"] = min_price
        if max_price is not None:
            filters["max_price"] = max_price

        products = await product_service.get_by_filter(db_session, count, page, **filters)
        total = await product_service.count(db_session, **filters)
        
        return ProductListResponse(
            products=[ProductResponse.model_validate(product) for product in products],
            total=total,
        )

    @post()
    async def create_product(
        self,
        product_service: ProductService,
        db_session: AsyncSession,
        data: ProductCreate,
    ) -> ProductResponse:
        """
        Создать новый продукт.
        Args:
            product_service: Сервис для работы с продуктами
            db_session: Сессия базы данных
            data: Данные для создания продукта
            
        Returns:
            ProductResponse: Созданный продукт
            
        Raises:
            HTTPException: Если данные невалидны
        """
        try:
            product = await product_service.create(db_session, data)
            return ProductResponse.model_validate(product)
        except ValueError as e:
            from litestar.exceptions import HTTPException
            raise HTTPException(status_code=400, detail=str(e))

    @put("/{product_id:int}")
    async def update_product(
        self,
        product_service: ProductService,
        db_session: AsyncSession,
        data: ProductUpdate,
        product_id: int = Parameter(gt=0, description="ID продукта"),
    ) -> ProductResponse:
        """
        Обновить продукт.
        Args:
            product_service: Сервис для работы с продуктами
            db_session: Сессия базы данных
            product_id: ID продукта (int)
            data: Данные для обновления
            
        Returns:
            ProductResponse: Обновленный продукт
            
        Raises:
            NotFoundException: Если продукт не найден
            HTTPException: Если данные невалидны
        """
        try:
            product = await product_service.update(db_session, product_id, data)
            return ProductResponse.model_validate(product)
        except ValueError as e:
            error_message = str(e)
            if "not found" in error_message.lower():
                raise NotFoundException(detail=error_message)
            from litestar.exceptions import HTTPException
            raise HTTPException(status_code=400, detail=error_message)

    @delete("/{product_id:int}")
    async def delete_product(
        self,
        product_service: ProductService,
        db_session: AsyncSession,
        product_id: int = Parameter(gt=0, description="ID продукта"),
    ) -> None:
        """
        Удалить продукт.
        Args:
            product_service: Сервис для работы с продуктами
            db_session: Сессия базы данных
            product_id: ID продукта (int)
            
        Raises:
            NotFoundException: Если продукт не найден
        """
        try:
            await product_service.delete(db_session, product_id)
        except ValueError as e:
            raise NotFoundException(detail=str(e))

