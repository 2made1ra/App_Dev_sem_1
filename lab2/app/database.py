from sqlalchemy import create_engine
from dotenv import load_dotenv
import os


load_dotenv()

DATABASE_URL = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5433/{os.getenv('POSTGRES_DB')}"

engine = create_engine(
    DATABASE_URL,
    echo=True  # Включает логирование SQL-запросов в консоль
)
