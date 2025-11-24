from datetime import datetime

from database import get_session
from models import Address, Order, Product, User
from sqlalchemy.orm import joinedload

products = [
    Product(
        name="Laptop",
        description="High-performance laptop",
        price=1200.00,
        stock_quantity=10,
        created_at=datetime.now(),
    ),
    Product(
        name="Mouse",
        description="Wireless mouse",
        price=25.50,
        stock_quantity=50,
        created_at=datetime.now(),
    ),
    Product(
        name="Keyboard",
        description="Mechanical keyboard",
        price=75.00,
        stock_quantity=30,
        created_at=datetime.now(),
    ),
    Product(
        name="Monitor",
        description="27-inch 4K monitor",
        price=350.00,
        stock_quantity=15,
        created_at=datetime.now(),
    ),
    Product(
        name="Headphones",
        description="Noise-cancelling headphones",
        price=150.00,
        stock_quantity=25,
        created_at=datetime.now(),
    ),
]

with get_session() as session:
    users = session.query(User).options(joinedload(User.addresses)).all()

    session.add_all(products)
    session.flush()

    orders = []
    for i, product in enumerate(products):
        user = users[i % len(users)]
        address = user.addresses[0]
        quantity = i + 1
        orders.append(
            Order(
                user_id=user.id,
                product_id=product.id,
                delivery_address_id=address.id,
                quantity=quantity,
                total_price=product.price * quantity,
                status="pending",
                order_date=datetime.now(),
                created_at=datetime.now(),
            )
        )

    session.add_all(orders)
    session.commit()

print("Success!")
