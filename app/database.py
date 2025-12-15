from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Use a default SQLite URL for local dev if SUPABASE_URL is not set, or prompt user to set it.
# For this MVP generation, we'll default to SQLite to ensure it runs immediately without config.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reportpilot.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
