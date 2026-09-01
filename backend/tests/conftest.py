import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.database import get_db, Base
import uuid

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Create the tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop the tables (not strictly necessary for in-memory, but good practice)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def user1_token(client):
    email = f"user1_{uuid.uuid4()}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "User 1"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return resp.json()["access_token"]

@pytest.fixture(scope="module")
def user2_token(client):
    email = f"user2_{uuid.uuid4()}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!", "full_name": "User 2"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return resp.json()["access_token"]
