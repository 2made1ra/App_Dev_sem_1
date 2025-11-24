from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    username: Mapped[str] = mapped_column(nullable=False, unique=True)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True) # новое поле
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # Связь с таблицей адресов
    addresses = relationship("Address", back_populates="user")
    orders = relationship("Order", back_populates="user")

class Address(Base):
    __tablename__ = 'addresses'
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
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

class Product(Base):
    __tablename__ = 'products'
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    price: Mapped[float] = mapped_column(nullable=False)
    stock_quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.now, onupdate=datetime.now)

    # связь с элементами заказов
    order_items = relationship("OrderItem", back_populates="product")


class OrderItem(Base):
    """Промежуточная таблица для связи Order и Product (many-to-many)."""
    __tablename__ = 'order_items'
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    order_id: Mapped[UUID] = mapped_column(ForeignKey('orders.id'), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey('products.id'), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    price_at_order: Mapped[float] = mapped_column(nullable=False)  # Цена на момент заказа
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    
    # Связи
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Order(Base):
    __tablename__ = 'orders'
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    delivery_address_id: Mapped[UUID] = mapped_column(ForeignKey('addresses.id'), nullable=False)
    
    total_price: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="pending")
    order_date: Mapped[datetime] = mapped_column(default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(default=datetime.now, onupdate=datetime.now)
    
    # Связи с другими таблицами
    user = relationship("User", back_populates="orders")
    delivery_address = relationship("Address")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
