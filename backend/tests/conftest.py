import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_engine):
    testing_session = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.get("/api/auth/csrf")
        yield test_client
    app.dependency_overrides.clear()


def register(client, email="player@example.com", username="player"):
    return client.post("/api/auth/register", json={"email": email, "username": username, "password": "very-secure-test-pass"})


def send(client, method, url, **kwargs):
    headers = kwargs.pop("headers", {})
    csrf = client.cookies.get("gametracker_csrf")
    if csrf:
        headers["X-CSRF-Token"] = csrf
    return client.request(method, url, headers=headers, **kwargs)
