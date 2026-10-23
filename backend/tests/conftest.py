import pytest
from fastapi.testclient import TestClient

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, session_factory


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-with-at-least-32-characters")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("TASK_MODE", "inline")
    get_settings.cache_clear()
    session_factory.cache_clear()
    factory = session_factory()
    Base.metadata.create_all(factory.kw["bind"])
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
    factory.kw["bind"].dispose()
    session_factory.cache_clear()
    get_settings.cache_clear()


def register(client, email="owner@example.in"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "a-long-test-password",
            "business_name": "Example Foods",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
