from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from contextlib import contextmanager


load_dotenv()

DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5433/{os.getenv('POSTGRES_DB')}"

engine = create_engine(
    DATABASE_URL,
    echo=True # Логирование SQL-запросов в консоль
)

session_factory = sessionmaker(engine)

@contextmanager
def get_session():
    session = session_factory()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


