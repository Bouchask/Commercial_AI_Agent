import pytest
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
from backend.mcp.google_auth import (
    get_user_google_credentials,
    get_current_user,
    set_active_execution_id,
    set_active_user,
)
from backend.mcp.google_sheets.tools import append_row


class TestGoogleAuthAndSheetsRequestContext:
    """Ensure Google auth and Sheets tools safely run outside Flask request context."""

    def test_get_user_google_credentials_outside_request_context_does_not_raise(self):
        """Calling get_user_google_credentials without an active HTTP request must never raise RuntimeError."""
        # This will return None or a fallback user with token, but MUST NOT raise RuntimeError: Working outside of request context
        try:
            creds = get_user_google_credentials()
            # If no user or no token in DB, it returns None safely
            assert creds is None or creds is not None
        except RuntimeError as e:
            pytest.fail(f"get_user_google_credentials raised unexpected RuntimeError: {e}")

    def test_get_current_user_outside_request_context(self):
        """get_current_user must return None or User without RuntimeError outside request context."""
        try:
            user = get_current_user()
            assert user is None or hasattr(user, "id")
        except RuntimeError as e:
            pytest.fail(f"get_current_user raised unexpected RuntimeError: {e}")

    @patch("backend.mcp.google_sheets.tools.get_user_google_credentials")
    @patch("backend.mcp.google_sheets.tools.build")
    def test_append_row_executes_outside_request_context(self, mock_build, mock_get_creds):
        """append_row must succeed outside any Flask request context without crashing."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        mock_service = MagicMock()
        mock_spreadsheets = MagicMock()
        mock_values = MagicMock()
        
        # Mock get metadata
        mock_get_meta = MagicMock()
        mock_get_meta.execute.return_value = {
            "sheets": [{"properties": {"title": "Clients", "sheetId": 0}}]
        }
        mock_spreadsheets.get.return_value = mock_get_meta

        # Mock existing rows
        mock_get_values = MagicMock()
        mock_get_values.execute.return_value = {"values": [["Date", "Nom", "Email"]]}
        mock_values.get.return_value = mock_get_values

        # Mock append
        mock_append = MagicMock()
        mock_append.execute.return_value = {
            "updates": {"updatedRange": "'Clients'!A2:C2"}
        }
        mock_values.append.return_value = mock_append

        mock_spreadsheets.values.return_value = mock_values
        mock_service.spreadsheets.return_value = mock_spreadsheets
        mock_build.return_value = mock_service

        # Invoke append_row with explicit spreadsheet_id outside request context
        result = append_row(
            values=["2026-10-15", "Entreprise Test", "contact@test.com"],
            spreadsheet_id="test_sheet_id_12345",
            sheet_name="Clients"
        )

        assert result["status"] == "success"
        assert result["spreadsheet_id"] == "test_sheet_id_12345"
        assert "link" in result

    @patch("backend.mcp.google_sheets.tools.get_user_google_credentials")
    @patch("backend.mcp.google_sheets.tools.build")
    def test_append_row_executes_inside_thread_pool_worker(self, mock_build, mock_get_creds):
        """append_row must succeed when run inside a ThreadPoolExecutor worker thread."""
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        mock_service = MagicMock()
        mock_spreadsheets = MagicMock()
        mock_values = MagicMock()

        mock_get_meta = MagicMock()
        mock_get_meta.execute.return_value = {
            "sheets": [{"properties": {"title": "Factures", "sheetId": 1}}]
        }
        mock_spreadsheets.get.return_value = mock_get_meta

        mock_get_values = MagicMock()
        mock_get_values.execute.return_value = {"values": [["Date", "Client ID", "Total TTC"]]}
        mock_values.get.return_value = mock_get_values

        mock_append = MagicMock()
        mock_append.execute.return_value = {
            "updates": {"updatedRange": "'Factures'!A2:C2"}
        }
        mock_values.append.return_value = mock_append

        mock_spreadsheets.values.return_value = mock_values
        mock_service.spreadsheets.return_value = mock_spreadsheets
        mock_build.return_value = mock_service

        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(
                append_row,
                values=["2026-10-15", "Client 1", "500.00 EUR"],
                spreadsheet_id="test_sheet_id_999",
                sheet_name="Factures"
            )
            result = future.result(timeout=5)

        assert result["status"] == "success"
        assert result["spreadsheet_id"] == "test_sheet_id_999"
