from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Схема для создания нового пользователя."""
    
    username: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email адрес пользователя")
    description: str | None = Field(None, max_length=500, description="Описание пользователя")


class UserUpdate(BaseModel):
    """Схема для обновления пользователя. Все поля опциональные."""
    
    username: str | None = Field(None, min_length=1, max_length=100, description="Имя пользователя")
    email: EmailStr | None = Field(None, description="Email адрес пользователя")
    description: str | None = Field(None, max_length=500, description="Описание пользователя")


class UserResponse(BaseModel):
    """Схема для ответа API с данными пользователя."""
    
    id: int = Field(..., gt=0, description="Уникальный идентификатор пользователя")
    username: str = Field(..., description="Имя пользователя")
    email: EmailStr = Field(..., description="Email адрес пользователя")
    description: str | None = Field(None, description="Описание пользователя")
    created_at: datetime = Field(..., description="Дата и время создания")
    updated_at: datetime | None = Field(None, description="Дата и время последнего обновления")
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Схема для ответа API со списком пользователей и общим количеством (задание со звездочкой)."""
    
    users: list[UserResponse] = Field(..., description="Список пользователей")
    total: int = Field(..., ge=0, description="Общее количество пользователей в базе данных")
