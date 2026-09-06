"""Standards-compliant MCP server for safe commercial-agent capabilities.

Run locally with ``python -m backend.mcp.standard_server``.  Mutating actions
(email, document creation, database writes) deliberately remain behind the
authenticated application workflow and its human-approval gate.
"""
from typing import Any

from mcp.server import MCPServer

from backend.mcp.database.tools import get_services
from backend.mcp.utils.tools import calculate, prepare_quote_items

mcp = MCPServer("Commercial AI Agent")


@mcp.tool()
def calculate_quote_expression(expression: str) -> dict[str, float]:
    """Safely evaluate a numeric commercial calculation expression."""
    return calculate(expression)


@mcp.tool()
def list_catalogue_services(codes: list[str] | None = None) -> list[dict[str, Any]]:
    """List the available commercial catalogue services, optionally by code."""
    return get_services(codes)


@mcp.tool()
def preview_quote_items(
    codes: list[str],
    quantities: dict[str, int] | None = None,
    discount_percent: float = 0.0,
    tax_rate: float = 0.20,
) -> dict[str, Any]:
    """Calculate quote lines and totals without creating a quote or document."""
    return prepare_quote_items(
        codes=codes,
        quantities=quantities,
        discount_percent=discount_percent,
        tax_rate=tax_rate,
    )


if __name__ == "__main__":
    mcp.run()
