import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Varsayılan: SQLite (kurulum gerektirmez, dosya olarak proje klasöründe oluşur).
# İstersen ortam değişkeni ile Postgres'e geçebilirsin, ör:
#   set DATABASE_URL=postgresql+psycopg2://postgres:sifre@localhost:5432/hatim_db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hatim.db")

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    pass
