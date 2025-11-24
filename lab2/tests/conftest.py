import pytest
from litestar.testing import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base
from app.repositories.user_repository import UserRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository
from main import app

# Тестовая база данных (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Создает движок для тестовой БД SQLite."""
    return create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(scope="session")
async def tables(engine):
    """Создает и удаляет таблицы для тестовой БД."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session(engine, tables):
    """Создает сессию БД для каждого теста."""
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def user_repository():
    """Фикстура для репозитория пользователей."""
    return UserRepository()


@pytest.fixture
def product_repository():
    """Фикстура для репозитория продуктов."""
    return ProductRepository()


@pytest.fixture
def order_repository():
    """Фикстура для репозитория заказов."""
    return OrderRepository()


@pytest.fixture
def client():
    """Фикстура для TestClient Litestar."""
    return TestClient(app=app)

