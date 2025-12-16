import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from litestar.testing import TestClient

from app.models import User
from app.schemas.user_schema import UserCreate
from app.repositories.user_repository import UserRepository


class TestUserController:
    """Тесты для API эндпоинтов пользователей."""

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self, client: TestClient, controller_session, user_repository: UserRepository
    ):
        """Тест GET /users/{user_id} - получение пользователя по ID."""
        # Создаем пользователя в БД
        user_data = UserCreate(
            email="test@example.com",
            username="test_user",
            description="Test user",
        )
        created_user = await user_repository.create(controller_session, user_data)
        await controller_session.commit()

        # Делаем запрос к API
        response = client.get(f"/users/{created_user.id}")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == created_user.id
        assert data["email"] == "test@example.com"
        assert data["username"] == "test_user"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, client: TestClient):
        """Тест GET /users/{user_id} - несуществующий пользователь."""
        response = client.get("/users/99999")

        assert response.status_code == HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_all_users(
        self, client: TestClient, controller_session, user_repository: UserRepository
    ):
        """Тест GET /users - получение списка пользователей."""
        # Создаем несколько пользователей
        for i in range(3):
            user_data = UserCreate(
                email=f"user{i}@example.com",
                username=f"user_{i}",
            )
            await user_repository.create(controller_session, user_data)
        await controller_session.commit()

        response = client.get("/users")

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert len(data["users"]) >= 3
        assert data["total"] >= 3

    @pytest.mark.asyncio
    async def test_get_all_users_with_pagination(
        self, client: TestClient, controller_session, user_repository: UserRepository
    ):
        """Тест GET /users - пагинация."""
        # Создаем 5 пользователей
        for i in range(5):
            user_data = UserCreate(
                email=f"paginated{i}@example.com",
                username=f"paginated_{i}",
            )
            await user_repository.create(controller_session, user_data)
        await controller_session.commit()

        # Первая страница
        response = client.get("/users?count=2&page=1")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["users"]) == 2

        # Вторая страница
        response = client.get("/users?count=2&page=2")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert len(data["users"]) == 2

    @pytest.mark.asyncio
    async def test_create_user(self, client: TestClient):
        """Тест POST /users - создание пользователя."""
        user_data = {
            "email": "new@example.com",
            "username": "new_user",
            "description": "New user description",
        }

        response = client.post("/users", json=user_data)

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["description"] == user_data["description"]
        assert "id" in data
        assert data["id"] > 0

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self, client: TestClient, controller_session, user_repository: UserRepository
    ):
        """Тест POST /users - создание пользователя с дублирующимся email."""
        # Создаем пользователя
        user_data = UserCreate(
            email="duplicate@example.com",
            username="first_user",
        )
        await user_repository.create(controller_session, user_data)
        await controller_session.commit()

        # Пытаемся создать еще одного с тем же email
        new_user_data = {
            "email": "duplicate@example.com",
            "username": "second_user",
        }

        response = client.post("/users", json=new_user_data)

        assert response.status_code == HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already exists" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_user(
        self, client: TestClient, controller_session, user_repository: UserRepository
    ):
        """Тест PUT /users/{user_id} - обновление пользователя."""
        # Создаем пользователя
        user_data = UserCreate(
            email="update@example.com",
            username="update_user",
            description="Original description",
        )
        created_user = await user_repository.create(controller_session, user_data)
        await controller_session.commit()

        # Обновляем пользователя
        update_data = {
            "description": "Updated description",
        }

        response = client.put(f"/users/{created_user.id}", json=update_data)

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == created_user.id
        assert data["description"] == "Updated description"
        assert data["email"] == "update@example.com"  # Не изменилось

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, client: TestClient):
        """Тест PUT /users/{user_id} - обновление несуществующего пользователя."""
        update_data = {"username": "new_username"}

        response = client.put("/users/99999", json=update_data)

        assert response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_user(
        self, client: TestClient, controller_session, user_repository: UserRepository
    ):
        """Тест DELETE /users/{user_id} - удаление пользователя."""
        # Создаем пользователя
        user_data = UserCreate(
            email="delete@example.com",
            username="delete_user",
        )
        created_user = await user_repository.create(controller_session, user_data)
        await controller_session.commit()

        # Удаляем пользователя
        response = client.delete(f"/users/{created_user.id}")

        assert response.status_code == HTTP_204_NO_CONTENT

        # Проверяем, что пользователь удален
        get_response = client.get(f"/users/{created_user.id}")
        assert get_response.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, client: TestClient):
        """Тест DELETE /users/{user_id} - удаление несуществующего пользователя."""
        response = client.delete("/users/99999")

        assert response.status_code == HTTP_404_NOT_FOUND

