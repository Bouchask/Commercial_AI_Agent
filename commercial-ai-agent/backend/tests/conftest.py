"""
Pytest configuration and fixtures for Commercial AI Agent tests.
"""
import pytest
import os
import sys
from unittest.mock import Mock, MagicMock, patch
import jwt
import datetime

# The database engine is created during module imports, so its URL must be set
# before importing application modules.  A test run must never contact a
# developer's configured remote database.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.app_improved import create_app
from backend.config.settings import settings
from backend.database.connection import SessionLocal, engine
from backend.models.base import Base
from backend.models.user import User
from backend.logging_config import setup_logging, CorrelationIDFilter
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment once per session."""
    # Setup logging for tests
    setup_logging(app_env="development")
    
    # Override settings for testing
    settings.DATABASE_URL = "sqlite:///:memory:"
    settings.JWT_SECRET = "test-secret-key"
    settings.APP_ENV = "testing"
    
    yield
    
    # Cleanup
    CorrelationIDFilter.clear_correlation_id()


@pytest.fixture
def test_app():
    """Create and configure test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    yield app
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_app):
    """Flask test client."""
    return test_app.test_client()


@pytest.fixture
def db_session():
    """Database session for tests."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    # Create tables
    Base.metadata.create_all(bind=connection)
    
    yield session
    
    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(
        email="test@example.com",
        hashed_password=generate_password_hash("testpass123"),
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Generate JWT token for test user."""
    token = jwt.encode({
        "sub": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, settings.JWT_SECRET, algorithm="HS256")
    return token


@pytest.fixture
def auth_headers(auth_token):
    """Authorization headers with JWT token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = MagicMock()
    provider.generate.return_value = "Generated response"
    provider.generate_json.return_value = {"status": "success"}
    return provider


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client."""
    client = MagicMock()
    client.invoke.return_value = {"success": True, "data": {}}
    return client


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator."""
    orchestrator = MagicMock()
    orchestrator.process_request.return_value = {
        "status": "completed",
        "results": {}
    }
    orchestrator.process_approval.return_value = {
        "status": "executing",
        "message": "Approved"
    }
    orchestrator.get_execution_status.return_value = {
        "execution_id": "exec-123",
        "status": "completed"
    }
    return orchestrator


@pytest.fixture
def sample_plan():
    """Sample execution plan."""
    return {
        "steps": [
            {
                "id": 1,
                "tool": "db.find_or_create_client",
                "arguments": {"name": "John Doe"},
                "depends_on": []
            },
            {
                "id": 2,
                "tool": "db.create_quote",
                "arguments": {"client_id": "{{step1.id}}", "amount": 5000},
                "depends_on": [1]
            }
        ]
    }


@pytest.fixture
def sample_execution_result():
    """Sample execution result."""
    return {
        "status": "completed",
        "results": {
            1: {"success": True, "data": {"id": 123, "name": "John Doe"}},
            2: {"success": True, "data": {"id": 456, "quote_id": "QTE-001"}}
        }
    }


# Test markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "e2e: end-to-end tests")
    config.addinivalue_line("markers", "slow: slow tests")
    config.addinivalue_line("markers", "security: security tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "db: database tests")
    config.addinivalue_line("markers", "llm: LLM provider tests")
    config.addinivalue_line("markers", "execution: execution tests")


# Helper functions
def assert_error_response(response, expected_error_code: str, status_code: int):
    """Assert error response format."""
    assert response.status_code == status_code
    data = response.get_json()
    assert "error" in data
    assert data["error"] == expected_error_code
    assert "message" in data
    assert "request_id" in data


def assert_success_response(response, status_code: int = 200):
    """Assert successful response."""
    assert response.status_code == status_code
    data = response.get_json()
    assert "error" not in data or data.get("status") in ["ok", "completed"]
