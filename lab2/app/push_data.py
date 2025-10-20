from database import get_session
from models import User, Address

users_data = [
    User(
        username="alice",
        email="alice@example.com",
        addresses=[
            Address(street="Main St, 1", city="Springfield", state="IL", zip_code="62701", country="USA", is_primary=True),
            Address(street="2nd St, 22", city="Springfield", state="IL", zip_code="62702", country="USA", is_primary=False),
        ]
    ),
    User(
        username="bob",
        email="bob@example.com",
        addresses=[
            Address(street="Oak Ave, 5", city="Shelbyville", state="IL", zip_code="62565", country="USA", is_primary=True),
        ]
    ),
    User(
        username="amelie",
        email="amelie@example.fr",
        addresses=[
            Address(street="12 Rue de Rivoli", city="Paris", state="Île-de-France", zip_code="75001", country="France", is_primary=True),
            Address(street="15 Avenue des Champs-Élysées", city="Paris", state="Île-de-France", zip_code="75008", country="France", is_primary=False),
        ]
    ),
    User(
        username="yuki",
        email="yuki@example.jp",
        addresses=[
            Address(street="1 Chome-1-2 Oshiage", city="Sumida City", state="Tokyo", zip_code="131-0045", country="Japan", is_primary=True),
        ]
    ),
    User(
        username="lucas",
        email="lucas@example.br",
        addresses=[
            Address(street="Av. Paulista, 1000", city="São Paulo", state="SP", zip_code="01310-100", country="Brazil", is_primary=True),
            Address(street="Rua Oscar Freire, 200", city="São Paulo", state="SP", zip_code="01426-001", country="Brazil", is_primary=False),
        ]
    ),
]


with get_session() as session:
    session.add_all(users_data)
    session.commit()

print('Data added successfully')
    