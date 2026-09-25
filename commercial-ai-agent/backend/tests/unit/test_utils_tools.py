"""Tests for the utils MCP tools (calculate, prepare_quote_items)."""
import pytest
from unittest.mock import patch


class TestCalculate:
    """Test utils.calculate tool."""

    def test_simple_addition(self):
        from backend.mcp.utils.tools import calculate
        result = calculate("2 + 3")
        assert result["result"] == 5

    def test_multiplication(self):
        from backend.mcp.utils.tools import calculate
        result = calculate("10 * 5")
        assert result["result"] == 50

    def test_decimal_division(self):
        from backend.mcp.utils.tools import calculate
        result = calculate("100 / 3")
        assert abs(result["result"] - 33.333) < 0.01


@patch("backend.mcp.database.tools.get_services")
class TestPrepareQuoteItems:
    """Test utils.prepare_quote_items tool."""

    def test_single_item_no_discount(self, mock_get_services):
        mock_get_services.return_value = [
            {"id": 1, "code": "WEB-SHOW", "name": "Site Web", "unit_price": 5000, "tax_rate": 0.20}
        ]
        from backend.mcp.utils.tools import prepare_quote_items
        result = prepare_quote_items(
            codes=["WEB-SHOW"],
            quantities={"WEB-SHOW": 1},
            discount_percent=0.0,
            tax_rate=0.20
        )
        assert result["total_ht"] == 5000
        assert result["tax"] == 1000  # 20% of 5000
        assert result["total_ttc"] == 6000

    def test_with_discount(self, mock_get_services):
        mock_get_services.return_value = [
            {"id": 2, "code": "APP-MOB", "name": "Service", "unit_price": 10000, "tax_rate": 0.20}
        ]
        from backend.mcp.utils.tools import prepare_quote_items
        result = prepare_quote_items(
            codes=["APP-MOB"],
            quantities={"APP-MOB": 1},
            discount_percent=0.10,
            tax_rate=0.20
        )
        assert result["total_ht"] == 9000  # 10000 - 10%
        assert result["tax"] == 1800  # 20% of 9000
        assert result["total_ttc"] == 10800

    def test_multiple_items(self, mock_get_services):
        mock_get_services.return_value = [
            {"id": 1, "code": "WEB-SHOW", "name": "Web", "unit_price": 5000, "tax_rate": 0.20},
            {"id": 3, "code": "SEO-OPT", "name": "SEO", "unit_price": 3000, "tax_rate": 0.20}
        ]
        from backend.mcp.utils.tools import prepare_quote_items
        result = prepare_quote_items(
            codes=["WEB-SHOW", "SEO-OPT"],
            quantities={"WEB-SHOW": 1, "SEO-OPT": 3},
            discount_percent=0.0,
            tax_rate=0.20
        )
        # 5000 + (3 * 3000) = 14000
        assert result["total_ht"] == 14000
        assert len(result["items"]) == 2

    def test_items_output_contains_required_fields(self, mock_get_services):
        mock_get_services.return_value = [
            {"id": 4, "code": "CONSULT", "name": "Test", "unit_price": 1000, "tax_rate": 0.20}
        ]
        from backend.mcp.utils.tools import prepare_quote_items
        result = prepare_quote_items(
            codes=["CONSULT"],
            quantities={"CONSULT": 2},
            discount_percent=0.05,
            tax_rate=0.20
        )
        assert "items" in result
        assert "total_ht" in result
        assert "tax" in result
        assert "total_ttc" in result
        assert "discount_percent_val" in result or "discount_percent" in result
