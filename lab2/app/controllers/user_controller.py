from litestar import Controller, get, post, put, delete
from litestar.di import Provide
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundException
from app.schemas.user_schema import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)
from app.services.user_service import UserService


class UserController(Controller):
    """Контроллер для управления пользователями."""

    path = "/users"

    @get("/{user_id:int}")
    async def get_user_by_id(
        self,
        user_service: UserService,
        db_session: AsyncSession,
        user_id: int = Parameter(
            gt=0,
            description="ID пользователя"
        ),
    ) -> UserResponse:
        """
        Получить пользователя по ID.
        Args:
            user_service: Сервис для работы с пользователями
            db_session: Сессия базы данных
            user_id: ID пользователя (int)
            
        Returns:
            UserResponse: Данные пользователя
            
        Raises:
            NotFoundException: Если пользователь не найден
        """
        user = await user_service.get_by_id(db_session, user_id)
        if not user:
            raise NotFoundException(
                detail=f"User with ID {user_id} not found"
            )
        return UserResponse.model_validate(user)

    @get()
    async def get_all_users(
        self,
        user_service: UserService,
        db_session: AsyncSession,
        count: int = Parameter(
            default=10, ge=1, le=100, description="Количество записей на странице"
        ),
        page: int = Parameter(
            default=1, ge=1, description="Номер страницы (начинается с 1)"
        ),
    ) -> UserListResponse:
        """
        Получить список пользователей с пагинацией.
        Args:
            user_service: Сервис для работы с пользователями
            db_session: Сессия базы данных
            count: Количество записей на странице (1-100)
            page: Номер страницы (начинается с 1)
            
        Returns:
            UserListResponse: Список пользователей и общее количество (задание со звездочкой)
        """
        users = await user_service.get_by_filter(db_session, count, page)
        total = await user_service.count(db_session)
        
        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total,
        )

    @post()
    async def create_user(
        self,
        user_service: UserService,
        db_session: AsyncSession,
        user_data: UserCreate,
    ) -> UserResponse:
        """
        Создать нового пользователя.
        Args:
            user_service: Сервис для работы с пользователями
            db_session: Сессия базы данных
            user_data: Данные для создания пользователя
            
        Returns:
            UserResponse: Созданный пользователь
            
        Raises:
            HTTPException: Если email или username уже существуют
        """
        try:
            user = await user_service.create(db_session, user_data)
            return UserResponse.model_validate(user)
        except ValueError as e:
            from litestar.exceptions import HTTPException
            raise HTTPException(status_code=400, detail=str(e))

    @put("/{user_id:int}")
    async def update_user(
        self,
        user_service: UserService,
        db_session: AsyncSession,
        user_data: UserUpdate,
        user_id: int = Parameter(gt=0, description="ID пользователя"),
    ) -> UserResponse:
        """
        Обновить пользователя.
        Args:
            user_service: Сервис для работы с пользователями
            db_session: Сессия базы данных
            user_id: ID пользователя (int)
            user_data: Данные для обновления
            
        Returns:
            UserResponse: Обновленный пользователь
            
        Raises:
            NotFoundException: Если пользователь не найден
            HTTPException: Если email или username уже существуют
        """
        try:
            user = await user_service.update(db_session, user_id, user_data)
            return UserResponse.model_validate(user)
        except ValueError as e:
            error_message = str(e)
            if "not found" in error_message.lower():
                raise NotFoundException(detail=error_message)
            from litestar.exceptions import HTTPException
            raise HTTPException(status_code=400, detail=error_message)

    @delete("/{user_id:int}")
    async def delete_user(
        self,
        user_service: UserService,
        db_session: AsyncSession,
        user_id: int = Parameter(gt=0, description="ID пользователя"),
    ) -> None:
        """
        Удалить пользователя.
        Args:
            user_service: Сервис для работы с пользователями
            db_session: Сессия базы данных
            user_id: ID пользователя (int)
            
        Raises:
            NotFoundException: Если пользователь не найден
        """
        try:
            await user_service.delete(db_session, user_id)
        except ValueError as e:
            raise NotFoundException(detail=str(e))

