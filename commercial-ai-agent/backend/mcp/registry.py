from typing import Dict, List, Optional
import logging
from backend.mcp.schemas import ToolSchema

class MCPRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSchema] = {}

    def register_tool(self, tool: ToolSchema) -> None:
        """Register a tool with its schema and handler."""
        if not tool.name or not tool.handler:
            raise ValueError("MCP tools require both a name and handler")
        existing = self._tools.get(tool.name)
        if existing and existing.handler is not tool.handler:
            logging.getLogger(__name__).warning("Replacing MCP tool registration: %s", tool.name)
        self._tools[tool.name] = tool

    def clear(self) -> None:
        """Clear registrations. Intended for isolated tests only."""
        self._tools.clear()

    def get_tool(self, name: str) -> Optional[ToolSchema]:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolSchema]:
        """List all registered tools."""
        return list(self._tools.values())
        
    def get_planner_tools(self) -> List[Dict]:
        """Format the registered tools for the Planner LLM prompt."""
        tools = []
        for tool in self.list_tools():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })
        return tools

# Global registry instance
registry = MCPRegistry()
