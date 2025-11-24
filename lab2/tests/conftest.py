import pytest
from litestar.testing import TestClient
from litestar.di import Provide
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base
from app.repositories.user_repository import UserRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository
from app.services.user_service import UserService
from app.services.product_service import ProductService
from app.services.order_service import OrderService
from main import app

# Тестовая база данных (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Глобальная переменная для тестового движка
_test_engine = None
_test_session_factory = None
# Глобальная переменная для текущей тестовой сессии
_current_test_session = None


@pytest.fixture(scope="session")
def engine():
    """Создает движок для тестовой БД SQLite."""
    global _test_engine
    _test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    return _test_engine


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
    """Создает сессию БД для каждого теста с изоляцией через транзакцию."""
    global _test_session_factory
    if _test_session_factory is None:
        _test_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async with _test_session_factory() as session:
        # Очищаем данные перед каждым тестом для полной изоляции
        async with session.begin():
            from sqlalchemy import text
            await session.execute(text("DELETE FROM order_items"))
            await session.execute(text("DELETE FROM orders"))
            await session.execute(text("DELETE FROM addresses"))
            await session.execute(text("DELETE FROM products"))
            await session.execute(text("DELETE FROM users"))
        
        # Начинаем транзакцию для изоляции
        trans = await session.begin()
        try:
            yield session
        finally:
            # Всегда откатываем транзакцию для изоляции тестов
            await trans.rollback()


@pytest.fixture
async def controller_session(engine, tables):
    """Создает сессию БД для тестов контроллеров с очисткой данных."""
    global _test_session_factory, _current_test_session
    if _test_session_factory is None:
        _test_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async with _test_session_factory() as session:
        # Очищаем данные перед тестом
        async with session.begin():
            from sqlalchemy import text
            await session.execute(text("DELETE FROM order_items"))
            await session.execute(text("DELETE FROM orders"))
            await session.execute(text("DELETE FROM addresses"))
            await session.execute(text("DELETE FROM products"))
            await session.execute(text("DELETE FROM users"))
        
        # Сохраняем сессию в глобальной переменной для использования в client
        _current_test_session = session
        try:
            yield session
        finally:
            _current_test_session = None
        
        # Очищаем данные после теста
        try:
            async with session.begin():
                from sqlalchemy import text
                await session.execute(text("DELETE FROM order_items"))
                await session.execute(text("DELETE FROM orders"))
                await session.execute(text("DELETE FROM addresses"))
                await session.execute(text("DELETE FROM products"))
                await session.execute(text("DELETE FROM users"))
        except Exception:
            pass


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


@pytest.fixture(scope="session")
def test_session_factory(engine):
    """Создает фабрику сессий для тестов."""
    return async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


async def provide_test_db_session(test_session_factory) -> AsyncSession:
    """Провайдер тестовой сессии БД для TestClient."""
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
def client(engine, tables):
    """Фикстура для TestClient Litestar с тестовой БД."""
    # Переопределяем зависимости для тестовой БД
    from app.dependencies import (
        provide_user_repository,
        provide_user_service,
        provide_product_repository,
        provide_product_service,
        provide_order_repository,
        provide_order_service,
    )
    
    # Используем ту же сессию, что и controller_session через глобальную переменную
    # Если controller_session не используется, создаем новую сессию для этого запроса
    async def provide_test_session() -> AsyncSession:
        global _current_test_session, _test_session_factory
        if _current_test_session is not None:
            # Используем существующую сессию из controller_session
            yield _current_test_session
        else:
            # Создаем новую сессию для тестов, которые не используют controller_session
            if _test_session_factory is None:
                from sqlalchemy.ext.asyncio import async_sessionmaker
                _test_session_factory = async_sessionmaker(
                    engine, class_=AsyncSession, expire_on_commit=False
                )
            async with _test_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
    
    # Создаем тестовое приложение с переопределенными зависимостями
    from litestar import Litestar
    from litestar.openapi import OpenAPIConfig
    
    # Получаем route handlers из основного приложения
    from app.controllers.user_controller import UserController
    from app.controllers.product_controller import ProductController
    from app.controllers.order_controller import OrderController
    
    test_app = Litestar(
        route_handlers=[
            UserController,
            ProductController,
            OrderController,
        ],
        dependencies={
            "db_session": Provide(provide_test_session),
            "user_repository": Provide(provide_user_repository),
            "user_service": Provide(provide_user_service),
            "product_repository": Provide(provide_product_repository),
            "product_service": Provide(provide_product_service),
            "order_repository": Provide(provide_order_repository),
            "order_service": Provide(provide_order_service),
        },
        openapi_config=OpenAPIConfig(
            title="E-Commerce API (Test)",
            version="1.0.0",
            description="Test API",
        ),
    )
    
    return TestClient(app=test_app)

