from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


async def provide_db_session() -> AsyncSession:
    """
    Провайдер сессии базы данных.
    
    Использует async context manager для управления жизненным циклом сессии.
    Сессия автоматически закрывается после завершения запроса.
    
    Yields:
        AsyncSession: Асинхронная сессия базы данных
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def provide_user_repository(
    db_session: AsyncSession
) -> UserRepository:
    """
    Провайдер репозитория пользователей.
    
    Args:
        db_session: Сессия базы данных (внедряется через DI)
        
    Returns:
        UserRepository: Экземпляр репозитория пользователей
    """
    return UserRepository()


async def provide_user_service(
    user_repository: UserRepository
) -> UserService:
    """
    Провайдер сервиса пользователей.
    
    Args:
        user_repository: Репозиторий пользователей (внедряется через DI)
        
    Returns:
        UserService: Экземпляр сервиса пользователей
    """
    return UserService(user_repository)

