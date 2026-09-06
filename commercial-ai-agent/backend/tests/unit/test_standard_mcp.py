"""Protocol-level verification of the official MCP server."""
import sys
from pathlib import Path

# Pytest places ``backend/`` on sys.path, where the legacy internal package
# named ``mcp`` would shadow the official SDK.  The application itself is run
# from the project root (``python -m backend...``), so remove that test-only
# path before importing the SDK.
backend_directory = Path(__file__).resolve().parents[2]
sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != backend_directory]

import pytest

from mcp import Client

from backend.mcp.standard_server import mcp


@pytest.mark.anyio
async def test_standard_mcp_server_lists_and_executes_safe_tool():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools.tools}
        assert {"calculate_quote_expression", "list_catalogue_services", "preview_quote_items"} <= tool_names

        result = await client.call_tool("calculate_quote_expression", {"expression": "1200 * 1.2"})
        assert result.structured_content == {"result": 1440.0}
