import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserUpdate


class TestUserRepository:
    """Тесты для репозитория пользователей."""

    @pytest.mark.asyncio
    async def test_create_user(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест создания пользователя в репозитории."""
        user_data = UserCreate(
            email="test@example.com",
            username="john_doe",
            description="Test user",
        )

        user = await user_repository.create(session, user_data)
        await session.commit()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "john_doe"
        assert user.description == "Test user"

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест получения пользователя по ID."""
        user_data = UserCreate(
            email="getbyid@example.com",
            username="getbyid_user",
            description="User for get_by_id test",
        )
        created_user = await user_repository.create(session, user_data)
        await session.commit()

        found_user = await user_repository.get_by_id(session, created_user.id)

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "getbyid@example.com"
        assert found_user.username == "getbyid_user"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест получения несуществующего пользователя по ID."""
        found_user = await user_repository.get_by_id(session, 99999)

        assert found_user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест получения пользователя по email."""
        user_data = UserCreate(
            email="unique@example.com",
            username="user_test",
            description="Test user",
        )
        created_user = await user_repository.create(session, user_data)
        await session.commit()

        # Ищем через get_by_filter с фильтром email
        users = await user_repository.get_by_filter(
            session, count=10, page=1, email="unique@example.com"
        )

        assert len(users) == 1
        assert users[0].id == created_user.id
        assert users[0].email == "unique@example.com"

    @pytest.mark.asyncio
    async def test_update_user(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест обновления пользователя."""
        user_data = UserCreate(
            email="update@example.com",
            username="test",
            description="Original description",
        )
        created_user = await user_repository.create(session, user_data)
        await session.commit()

        update_data = UserUpdate(description="Updated description")
        updated_user = await user_repository.update(
            session, created_user.id, update_data
        )
        await session.commit()

        assert updated_user.id == created_user.id
        assert updated_user.username == "test"  # не изменилось
        assert updated_user.email == "update@example.com"  # не изменилось
        assert updated_user.description == "Updated description"  # изменилось

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест обновления несуществующего пользователя."""
        update_data = UserUpdate(username="new_username")

        with pytest.raises(ValueError, match="User with ID 99999 not found"):
            await user_repository.update(session, 99999, update_data)

    @pytest.mark.asyncio
    async def test_delete_user(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест удаления пользователя."""
        user_data = UserCreate(
            email="delete@example.com",
            username="delete_user",
            description="User to delete",
        )
        created_user = await user_repository.create(session, user_data)
        await session.commit()

        await user_repository.delete(session, created_user.id)
        await session.commit()

        deleted_user = await user_repository.get_by_id(session, created_user.id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест удаления несуществующего пользователя."""
        with pytest.raises(ValueError, match="User with ID 99999 not found"):
            await user_repository.delete(session, 99999)

    @pytest.mark.asyncio
    async def test_get_all_users(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест получения списка пользователей."""
        # Создаем несколько пользователей
        for i in range(5):
            user_data = UserCreate(
                email=f"user{i}@example.com",
                username=f"user_{i}",
                description=f"User {i}",
            )
            await user_repository.create(session, user_data)
        await session.commit()

        users = await user_repository.get_by_filter(session, count=10, page=1)
        total = await user_repository.count(session)

        assert len(users) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_get_all_users_with_pagination(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест получения списка пользователей с пагинацией."""
        # Создаем 10 пользователей
        for i in range(10):
            user_data = UserCreate(
                email=f"paginated{i}@example.com",
                username=f"paginated_{i}",
            )
            await user_repository.create(session, user_data)
        await session.commit()

        # Первая страница (5 записей)
        page1 = await user_repository.get_by_filter(session, count=5, page=1)
        assert len(page1) == 5

        # Вторая страница (5 записей)
        page2 = await user_repository.get_by_filter(session, count=5, page=2)
        assert len(page2) == 5

        # Проверяем, что записи разные
        page1_ids = {user.id for user in page1}
        page2_ids = {user.id for user in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_get_users_with_filter(
        self, session: AsyncSession, user_repository: UserRepository
    ):
        """Тест получения пользователей с фильтрацией."""
        # Создаем пользователей с разными username
        user_data1 = UserCreate(
            email="filter1@example.com",
            username="john_doe",
            description="First user",
        )
        user_data2 = UserCreate(
            email="filter2@example.com",
            username="jane_doe",
            description="Second user",
        )
        await user_repository.create(session, user_data1)
        await user_repository.create(session, user_data2)
        await session.commit()

        # Фильтр по username
        users = await user_repository.get_by_filter(
            session, count=10, page=1, username="john"
        )
        assert len(users) == 1
        assert users[0].username == "john_doe"

        # Фильтр по email
        users = await user_repository.get_by_filter(
            session, count=10, page=1, email="filter1"
        )
        assert len(users) == 1
        assert users[0].email == "filter1@example.com"

