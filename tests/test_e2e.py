import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200

def test_create_candidate():
    data = {
        "name": "Test Candidate",
        "email": "test@example.com",
        "preferred_roles": "Engineer",
        "preferred_locations": "Remote"
    }
    response = client.post("/candidate", json=data)
    assert response.status_code == 200

def test_get_candidate():
    response = client.get("/candidate/me")
    assert response.status_code == 200

def test_scheduler_status():
    response = client.get("/scheduler/status")
    assert response.status_code == 200

def test_dashboard_stats():
    response = client.get("/dashboard/stats")
    assert response.status_code == 200
