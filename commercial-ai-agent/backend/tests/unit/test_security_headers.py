"""Tests for security headers and middleware."""
import pytest
from unittest.mock import patch


@pytest.fixture
def app():
    """Create a minimal Flask app with middleware for testing."""
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite:///test_security.db")
    os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-minimum-32-chars")
    os.environ.setdefault("LLM_PROVIDER", "groq")
    os.environ.setdefault("GROQ_API_KEY", "test")
    os.environ.setdefault("APP_ENV", "test")

    from backend.api.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestSecurityHeaders:
    """Verify that all security headers are set on every response."""

    def test_x_content_type_options(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        resp = client.get("/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        resp = client.get("/health")
        assert resp.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"

    def test_correlation_id_in_response(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Correlation-ID") is not None


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code in (200, 503)
        data = resp.get_json()
        assert "status" in data
        assert "service" in data

    def test_health_returns_json(self, client):
        resp = client.get("/health")
        assert resp.content_type.startswith("application/json")


class TestErrorHandlers:
    """Test that custom error handlers work."""

    def test_404_returns_json(self, client):
        resp = client.get("/api/nonexistent-route-xyz")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "NOT_FOUND"

    def test_405_returns_json(self, client):
        resp = client.delete("/health")
        assert resp.status_code == 405
        data = resp.get_json()
        assert data["error"] == "METHOD_NOT_ALLOWED"
