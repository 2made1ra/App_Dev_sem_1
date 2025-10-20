from sqlalchemy import select
from database import get_session
from sqlalchemy.orm import selectinload
from models import User, Address



if __name__ == "__main__":
    with get_session() as session:
        users = select(User).options(selectinload(User.addresses))
        result = session.execute(users).scalars().all()
        print()
        for user in result:
            print(f"Пользователь: {user.username} ({user.email})")
            for addr in user.addresses:
                print(f"  - {addr.street}, {addr.city}, {addr.country} (Primary: {addr.is_primary})")