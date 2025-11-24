from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.user_schema import UserCreate, UserUpdate


class UserRepository:
    """Репозиторий для CRUD операций с пользователями."""

    async def get_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        """
        Получить пользователя по ID.

        Args:
            session: Асинхронная сессия базы данных
            user_id: ID пользователя (int)

        Returns:
            User объект или None, если не найден
        """
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

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
        stmt = select(User)

        if "username" in kwargs and kwargs["username"]:
            stmt = stmt.where(User.username.ilike(f"%{kwargs['username']}%"))
        if "email" in kwargs and kwargs["email"]:
            stmt = stmt.where(User.email.ilike(f"%{kwargs['email']}%"))

        offset = (page - 1) * count
        stmt = stmt.offset(offset).limit(count)

        stmt = stmt.order_by(User.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, session: AsyncSession, user_data: UserCreate) -> User:
        """
        Создать нового пользователя.

        Args:
            session: Асинхронная сессия базы данных
            user_data: Данные для создания пользователя

        Returns:
            Созданный объект User
        """
        user = User(
            username=user_data.username,
            email=user_data.email,
            description=user_data.description,
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user

    async def update(
        self, session: AsyncSession, user_id: int, user_data: UserUpdate
    ) -> User:
        """
        Обновить пользователя через ORM.

        Args:
            session: Асинхронная сессия базы данных
            user_id: ID пользователя (int)
            user_data: Данные для обновления (только переданные поля)

        Returns:
            Обновленный объект User

        Raises:
            ValueError: Если пользователь не найден
        """
        # Получаем объект пользователя через ORM
        user = await self.get_by_id(session, user_id)

        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Обновляем атрибуты объекта через ORM
        update_data = {
            k: v
            for k, v in user_data.model_dump(exclude_unset=True).items()
            if v is not None
        }

        for key, value in update_data.items():
            setattr(user, key, value)

        await session.flush()
        await session.refresh(user)
        return user

    async def delete(self, session: AsyncSession, user_id: int) -> None:
        """
        Удалить пользователя через ORM.

        Args:
            session: Асинхронная сессия базы данных
            user_id: ID пользователя (int)

        Raises:
            ValueError: Если пользователь не найден
        """
        user = await self.get_by_id(session, user_id)

        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Используем ORM delete
        await session.delete(user)
        await session.flush()

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
        stmt = select(func.count(User.id))

        if "username" in kwargs and kwargs["username"]:
            stmt = stmt.where(User.username.ilike(f"%{kwargs['username']}%"))
        if "email" in kwargs and kwargs["email"]:
            stmt = stmt.where(User.email.ilike(f"%{kwargs['email']}%"))

        result = await session.execute(stmt)
        return result.scalar_one() or 0
