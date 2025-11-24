import pytest
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.schemas.user_schema import UserCreate, UserUpdate


class TestUserService:
    """Тесты для сервиса пользователей с моками."""

    @pytest.fixture
    def mock_user_repository(self):
        """Создает мок репозитория пользователей."""
        return AsyncMock(spec=UserRepository)

    @pytest.fixture
    def mock_session(self):
        """Создает мок сессии БД."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def user_service(self, mock_user_repository):
        """Создает экземпляр сервиса с моком репозитория."""
        return UserService(mock_user_repository)

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест успешного получения пользователя по ID."""
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.username = "test_user"
        mock_user.email = "test@example.com"

        mock_user_repository.get_by_id.return_value = mock_user

        result = await user_service.get_by_id(mock_session, 1)

        assert result is not None
        assert result.id == 1
        assert result.username == "test_user"
        mock_user_repository.get_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест получения несуществующего пользователя."""
        mock_user_repository.get_by_id.return_value = None

        result = await user_service.get_by_id(mock_session, 999)

        assert result is None
        mock_user_repository.get_by_id.assert_called_once_with(mock_session, 999)

    @pytest.mark.asyncio
    async def test_create_user_success(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест успешного создания пользователя."""
        user_data = UserCreate(
            email="new@example.com",
            username="new_user",
            description="New user",
        )

        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = user_data.email
        mock_user.username = user_data.username
        mock_user.description = user_data.description

        # Мокаем проверку уникальности (email и username не существуют)
        # _check_email_exists и _check_username_exists используют session.execute напрямую
        # Для этого нужно замокать session.execute
        async def mock_execute(stmt):
            result_mock = Mock()
            result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_user_repository.create.return_value = mock_user

        result = await user_service.create(mock_session, user_data)

        assert result is not None
        assert result.id == 1
        assert result.email == user_data.email
        mock_user_repository.create.assert_called_once_with(mock_session, user_data)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест создания пользователя с дублирующимся email."""
        user_data = UserCreate(
            email="existing@example.com",
            username="new_user",
        )

        # Мокаем существующего пользователя с таким email
        existing_user = Mock(spec=User)
        existing_user.email = "existing@example.com"

        async def mock_execute(stmt):
            result_mock = Mock()
            # Первый вызов - проверка email (возвращает существующего пользователя)
            if "email" in str(stmt):
                result_mock.scalar_one_or_none.return_value = existing_user
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="User with email existing@example.com already exists"):
            await user_service.create(mock_session, user_data)

        mock_user_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест создания пользователя с дублирующимся username."""
        user_data = UserCreate(
            email="new@example.com",
            username="existing_user",
        )

        # Мокаем существующего пользователя с таким username
        existing_user = Mock(spec=User)
        existing_user.username = "existing_user"
        existing_user.email = "different@example.com"

        call_count = [0]  # Используем список для изменяемого счетчика

        async def mock_execute(stmt):
            result_mock = Mock()
            call_count[0] += 1
            # Первый вызов - проверка email (не найден)
            # Второй вызов - проверка username (найден)
            if call_count[0] == 1:
                # Проверка email
                result_mock.scalar_one_or_none.return_value = None
            elif call_count[0] == 2:
                # Проверка username
                result_mock.scalar_one_or_none.return_value = existing_user
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="User with username existing_user already exists"):
            await user_service.create(mock_session, user_data)

        mock_user_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_success(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест успешного обновления пользователя."""
        existing_user = Mock(spec=User)
        existing_user.id = 1
        existing_user.email = "old@example.com"
        existing_user.username = "old_user"

        updated_user = Mock(spec=User)
        updated_user.id = 1
        updated_user.email = "old@example.com"
        updated_user.username = "new_username"
        updated_user.description = "Updated description"

        update_data = UserUpdate(username="new_username", description="Updated description")

        mock_user_repository.get_by_id.return_value = existing_user
        mock_user_repository.update.return_value = updated_user

        # Мокаем проверку уникальности username
        async def mock_execute(stmt):
            result_mock = Mock()
            result_mock.scalar_one_or_none.return_value = None  # username свободен
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        result = await user_service.update(mock_session, 1, update_data)

        assert result.username == "new_username"
        assert result.description == "Updated description"
        mock_user_repository.update.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест обновления несуществующего пользователя."""
        update_data = UserUpdate(username="new_username")

        mock_user_repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="User with ID 999 not found"):
            await user_service.update(mock_session, 999, update_data)

        mock_user_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест обновления пользователя с дублирующимся email."""
        existing_user = Mock(spec=User)
        existing_user.id = 1
        existing_user.email = "old@example.com"
        existing_user.username = "old_user"

        update_data = UserUpdate(email="existing@example.com")

        mock_user_repository.get_by_id.return_value = existing_user

        # Мокаем существующего пользователя с таким email
        existing_user_with_email = Mock(spec=User)
        existing_user_with_email.id = 2
        existing_user_with_email.email = "existing@example.com"

        async def mock_execute(stmt):
            result_mock = Mock()
            if "email" in str(stmt):
                result_mock.scalar_one_or_none.return_value = existing_user_with_email
            else:
                result_mock.scalar_one_or_none.return_value = None
            return result_mock

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ValueError, match="User with email existing@example.com already exists"):
            await user_service.update(mock_session, 1, update_data)

        mock_user_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест успешного удаления пользователя."""
        mock_user_repository.delete.return_value = None

        await user_service.delete(mock_session, 1)

        mock_user_repository.delete.assert_called_once_with(mock_session, 1)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_filter(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест получения списка пользователей с фильтрацией."""
        mock_users = [
            Mock(spec=User, id=1, username="user1"),
            Mock(spec=User, id=2, username="user2"),
        ]

        mock_user_repository.get_by_filter.return_value = mock_users

        result = await user_service.get_by_filter(mock_session, count=10, page=1, username="user")

        assert len(result) == 2
        mock_user_repository.get_by_filter.assert_called_once_with(
            mock_session, 10, 1, username="user"
        )

    @pytest.mark.asyncio
    async def test_count(
        self, user_service: UserService, mock_session, mock_user_repository
    ):
        """Тест подсчета пользователей."""
        mock_user_repository.count.return_value = 5

        result = await user_service.count(mock_session, username="test")

        assert result == 5
        mock_user_repository.count.assert_called_once_with(mock_session, username="test")

