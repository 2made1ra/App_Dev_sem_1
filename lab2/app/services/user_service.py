import logging
from datetime import datetime

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.user_cache import (
    delete_user_from_cache,
    get_user_from_cache,
    set_user_to_cache,
)
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для бизнес-логики работы с пользователями."""

    def __init__(
        self, user_repository: UserRepository, redis_client: redis.Redis | None = None
    ):
        """
        Инициализация сервиса.
        Args:
            user_repository: Репозиторий для работы с пользователями (Dependency Injection)
            redis_client: Клиент Redis для кэширования (опционально)
        """
        self.user_repository = user_repository
        self.redis_client = redis_client

    async def get_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        """
        Получить пользователя по ID с использованием кэширования.
        Args:
            session: Асинхронная сессия базы данных
            user_id: ID пользователя (int)

        Returns:
            User объект или None, если не найден
        """
        # Попытка получить данные из кэша
        if self.redis_client:
            cached_data = get_user_from_cache(self.redis_client, user_id)
            if cached_data is not None:
                # Преобразуем словарь обратно в объект User
                # Преобразуем строки ISO формата обратно в datetime
                created_at = (
                    datetime.fromisoformat(cached_data["created_at"])
                    if isinstance(cached_data["created_at"], str)
                    else cached_data["created_at"]
                )
                updated_at = (
                    datetime.fromisoformat(cached_data["updated_at"])
                    if cached_data.get("updated_at")
                    and isinstance(cached_data["updated_at"], str)
                    else cached_data.get("updated_at")
                )
                return User(
                    id=cached_data["id"],
                    username=cached_data["username"],
                    email=cached_data["email"],
                    description=cached_data.get("description"),
                    created_at=created_at,
                    updated_at=updated_at,
                )

        # Если данных нет в кэше, получаем из БД
        user = await self.user_repository.get_by_id(session, user_id)
        if user and self.redis_client:
            # Сохраняем в кэш (обработка ошибок внутри функции)
            try:
                user_dict = UserResponse.model_validate(user).model_dump()
                # Преобразуем datetime в строки для JSON
                if user_dict.get("created_at"):
                    user_dict["created_at"] = user_dict["created_at"].isoformat()
                if user_dict.get("updated_at"):
                    user_dict["updated_at"] = user_dict["updated_at"].isoformat()
                set_user_to_cache(self.redis_client, user_id, user_dict)
            except (ValueError, TypeError, redis.RedisError) as e:
                # Логируем ошибку, но не блокируем возврат данных
                logger.warning(
                    "Не удалось сохранить пользователя в кэш: user_id=%s, error=%s",
                    user_id,
                    e,
                )

        return user

    async def get_by_filter(
        self, session: AsyncSession, count: int, page: int, **kwargs
    ) -> list[User]:
        """
        Получить список пользователей с пагинацией и фильтрацией.
        Args:
            session: Асинхронная сессия базы данных
            count: Количество записей на странице
            page: Номер страницы (начинается с 1)
            **kwargs: Фильтры (username, email)

        Returns:
            Список пользователей
        """
        return await self.user_repository.get_by_filter(session, count, page, **kwargs)

    async def create(self, session: AsyncSession, user_data: UserCreate) -> User:
        """
        Создать нового пользователя с проверкой уникальности.
        Args:
            session: Асинхронная сессия базы данных
            user_data: Данные для создания пользователя

        Returns:
            Созданный объект User

        Raises:
            ValueError: Если email или username уже существуют
        """
        existing_user = await self._check_email_exists(session, user_data.email)
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")

        existing_user = await self._check_username_exists(session, user_data.username)
        if existing_user:
            raise ValueError(f"User with username {user_data.username} already exists")

        user = await self.user_repository.create(session, user_data)
        await session.commit()
        return user

    async def update(
        self, session: AsyncSession, user_id: int, user_data: UserUpdate
    ) -> User:
        """
        Обновить пользователя с проверкой уникальности при изменении email/username.
        Args:
            session: Асинхронная сессия базы данных
            user_id: ID пользователя (int)
            user_data: Данные для обновления

        Returns:
            Обновленный объект User

        Raises:
            ValueError: Если пользователь не найден или email/username уже существуют
        """
        existing_user = await self.user_repository.get_by_id(session, user_id)
        if not existing_user:
            raise ValueError(f"User with ID {user_id} not found")

        if user_data.email and user_data.email != existing_user.email:
            user_with_email = await self._check_email_exists(session, user_data.email)
            if user_with_email:
                raise ValueError(f"User with email {user_data.email} already exists")

        if user_data.username and user_data.username != existing_user.username:
            user_with_username = await self._check_username_exists(
                session, user_data.username
            )
            if user_with_username:
                raise ValueError(
                    f"User with username {user_data.username} already exists"
                )

        user = await self.user_repository.update(session, user_id, user_data)
        await session.commit()

        # Инвалидация кэша после обновления (обработка ошибок внутри функции)
        if self.redis_client:
            try:
                delete_user_from_cache(self.redis_client, user_id)
            except redis.RedisError as e:
                # Логируем ошибку, но не блокируем возврат данных
                logger.warning(
                    "Не удалось удалить пользователя из кэша: user_id=%s, error=%s",
                    user_id,
                    e,
                )

        return user

    async def delete(self, session: AsyncSession, user_id: int) -> None:
        """
        Удалить пользователя.
        Args:
            session: Асинхронная сессия базы данных
            user_id: ID пользователя (int)

        Raises:
            ValueError: Если пользователь не найден
        """
        await self.user_repository.delete(session, user_id)
        await session.commit()

        # Инвалидация кэша после удаления (обработка ошибок внутри функции)
        if self.redis_client:
            try:
                delete_user_from_cache(self.redis_client, user_id)
            except redis.RedisError as e:
                # Логируем ошибку, но не блокируем удаление
                logger.warning(
                    "Не удалось удалить пользователя из кэша: user_id=%s, error=%s",
                    user_id,
                    e,
                )

    async def count(self, session: AsyncSession, **kwargs) -> int:
        """
        Получить общее количество пользователей с учетом фильтров.
        Используется для задания со звездочкой.
        Args:
            session: Асинхронная сессия базы данных
            **kwargs: Фильтры (username, email)

        Returns:
            Количество пользователей
        """
        return await self.user_repository.count(session, **kwargs)

    async def _check_email_exists(
        self, session: AsyncSession, email: str
    ) -> User | None:
        """
        Проверить, существует ли пользователь с указанным email.
        Args:
            session: Асинхронная сессия базы данных
            email: Email для проверки

        Returns:
            User объект или None, если не найден
        """
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _check_username_exists(
        self, session: AsyncSession, username: str
    ) -> User | None:
        """
        Проверить, существует ли пользователь с указанным username.
        Args:
            session: Асинхронная сессия базы данных
            username: Username для проверки

        Returns:
            User объект или None, если не найден
        """
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
