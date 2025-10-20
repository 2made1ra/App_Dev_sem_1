from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    username: Mapped[str] = mapped_column(nullable=False, unique=True)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # Связь с таблицей адресов
    addresses = relationship("Address", back_populates="user")

class Address(Base):
    __tablename__ = 'addresses'
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    street: Mapped[str] = mapped_column(nullable=False)
    city: Mapped[str] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column()
    zip_code: Mapped[str] = mapped_column()
    country: Mapped[str] = mapped_column(nullable=False)
    is_primary: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # Обратная связь с таблицей пользователей
    user = relationship("User", back_populates="addresses")

