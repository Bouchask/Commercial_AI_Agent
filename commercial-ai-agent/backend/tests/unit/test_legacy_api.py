"""Regression tests for the Flask app used by the Vercel entrypoint."""
import pytest

from backend.api.app import create_app as create_legacy_app
from backend.models.base import Base
from backend.database.connection import engine


@pytest.fixture
def legacy_client():
    Base.metadata.create_all(bind=engine)
    app = create_legacy_app()
    app.config["TESTING"] = True
    yield app.test_client()
    Base.metadata.drop_all(bind=engine)


def test_legacy_health_checks_database(legacy_client):
    response = legacy_client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["database"] == "connected"


def test_legacy_login_requires_json_credentials(legacy_client):
    response = legacy_client.post("/api/login", data="invalid", content_type="text/plain")

    assert response.status_code == 400
    assert response.get_json()["error"] == "INVALID_INPUT"
    assert response.get_json()["context"]["field"] == "Content-Type"


def test_legacy_chat_requires_token(legacy_client):
    response = legacy_client.post("/api/chat", json={"prompt": "Create a quote"})

    assert response.status_code == 401
