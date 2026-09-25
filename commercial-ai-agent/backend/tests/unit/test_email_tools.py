"""Tests for email tools validation and edge cases."""
import pytest
from unittest.mock import patch, MagicMock


class TestPrepareEmail:
    """Test email.prepare tool validation."""

    def test_prepare_email_valid(self):
        from backend.mcp.email.tools import prepare_email
        result = prepare_email(
            to="test@example.com",
            subject="Test Subject",
            body="Hello World"
        )
        assert result["status"] == "prepared"
        assert result["to"] == "test@example.com"
        assert result["subject"] == "Test Subject"
        assert result["body"] == "Hello World"
        assert result["attachments"] == []

    def test_prepare_email_rejects_empty_to(self):
        from backend.mcp.email.tools import prepare_email
        with pytest.raises(ValueError, match="missing"):
            prepare_email(to="", subject="Test", body="Hello")

    def test_prepare_email_rejects_none_to(self):
        from backend.mcp.email.tools import prepare_email
        with pytest.raises(ValueError, match="missing"):
            prepare_email(to="None", subject="Test", body="Hello")

    def test_prepare_email_rejects_invalid_format(self):
        from backend.mcp.email.tools import prepare_email
        with pytest.raises(ValueError, match="Invalid email"):
            prepare_email(to="not-an-email", subject="Test", body="Hello")

    def test_prepare_email_trims_whitespace(self):
        from backend.mcp.email.tools import prepare_email
        result = prepare_email(
            to="  test@example.com  ",
            subject="Test",
            body="Body"
        )
        assert result["to"] == "  test@example.com  "
        assert result["status"] == "prepared"


class TestSendEmail:
    """Test email.send tool with mocked SMTP/Gmail."""

    @patch("backend.mcp.email.tools.get_user_google_credentials", return_value=None)
    def test_send_email_rejects_invalid_format(self, mock_creds):
        from backend.mcp.email.tools import send_email
        with pytest.raises(ValueError, match="Invalid email"):
            send_email(to="not-an-email", subject="Test", body="Body")

    @patch("backend.mcp.email.tools.get_user_google_credentials", return_value=None)
    @patch.dict("os.environ", {"SMTP_USERNAME": "", "SMTP_PASSWORD": ""}, clear=True)
    def test_send_email_simulates_without_credentials(self, mock_creds):
        from backend.mcp.email.tools import send_email
        result = send_email(to="test@example.com", subject="Test", body="Body")
        assert result["status"] == "success"
        assert result["method"] == "simulation"
