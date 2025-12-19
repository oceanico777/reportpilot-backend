import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime
import uuid

# Set env vars for testing *before* importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret"
os.environ["GEMINI_API_KEY"] = "fake-key"
os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
os.environ["SUPABASE_KEY"] = "fake-key"

from app.database import Base, get_db
from app.main import app
from app.auth import get_current_user
from app.models import User, Company, Receipt, Report # Explicit import to register models

# Create file-based engine for debugging persistence
engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

@pytest.fixture
def user_payload():
    return {
        "sub": "test-user-id",
        "email": "test@example.com",
        "role": "authenticated",
        "user_metadata": {"full_name": "Test User"}
    }

@pytest.fixture
def auth_headers(user_payload):
    token = jwt.encode(user_payload, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_user_payload():
    return {
        "sub": "other-user-id",
        "email": "other@example.com",
        "role": "authenticated",
        "user_metadata": {"full_name": "Other User"}
    }

@pytest.fixture
def other_auth_headers(other_user_payload):
    token = jwt.encode(other_user_payload, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
