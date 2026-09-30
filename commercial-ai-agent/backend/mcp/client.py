import logging
import time
from typing import Dict, Any
from backend.mcp.registry import registry
from backend.mcp.schemas import ToolResult, ToolInputValidationError, validate_tool_arguments

class MCPClient:
    """Internal client to execute registered tools safely."""
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], execution_id: str) -> ToolResult:
        started_at = time.perf_counter()
        tool = registry.get_tool(tool_name)
        
        if not tool:
            result = ToolResult(
                success=False,
                tool=tool_name,
                execution_id=execution_id,
                error={"code": "TOOL_NOT_FOUND", "message": f"Tool {tool_name} is not registered."}
            )
            self._audit(result, started_at)
            return result
            
        if not tool.handler:
            result = ToolResult(
                success=False,
                tool=tool_name,
                execution_id=execution_id,
                error={"code": "HANDLER_NOT_FOUND", "message": f"Tool {tool_name} has no handler."}
            )
            self._audit(result, started_at)
            return result
            
        try:
            from backend.mcp.google_auth import set_active_execution_id
            set_active_execution_id(execution_id)
            
            validate_tool_arguments(arguments, tool.input_schema)
            data = tool.handler(**arguments)
            result = ToolResult(
                success=True,
                tool=tool_name,
                execution_id=execution_id,
                data=data
            )
            self._audit(result, started_at)
            return result
        except ToolInputValidationError as e:
            result = ToolResult(
                success=False,
                tool=tool_name,
                execution_id=execution_id,
                error={"code": "INVALID_TOOL_ARGUMENTS", "message": str(e)}
            )
            self._audit(result, started_at)
            return result
        except Exception as e:
            result = ToolResult(
                success=False,
                tool=tool_name,
                execution_id=execution_id,
                error={
                    "code": "TOOL_EXECUTION_ERROR",
                    "message": str(e)
                }
            )
            self._audit(result, started_at)
            return result

    def invoke(self, tool_name: str, arguments: Dict[str, Any], execution_id: str = None) -> Any:
        """Convenience wrapper used by the execution engine.

        Executes the registered tool and returns its data payload on success.
        On failure, raises a backend.exceptions.ToolError with structured context.
        """
        # Generate a short-lived execution id if caller didn't provide one
        execution_id = execution_id or f"exec-{int(time.time() * 1000)}"
        result = self.execute_tool(tool_name, arguments, execution_id=execution_id)

        if not result.success:
            # Raise a structured ToolError so callers can handle failures consistently
            try:
                from backend.exceptions import ToolError as BackendToolError
            except Exception:
                raise RuntimeError(f"Tool {tool_name} failed: {result.error}")

            err = result.error or {"message": "Unknown tool error"}
            raise BackendToolError(
                message=f"Tool '{tool_name}' execution failed: {err.get('message', err)}",
                tool_name=tool_name,
                tool_error=str(err)
            )

        return result.data

    @staticmethod
    def _audit(result: ToolResult, started_at: float) -> None:
        """Persist minimal, non-sensitive tool telemetry without blocking a tool call."""
        try:
            from backend.database.connection import SessionLocal
            from backend.models.audit_log import AuditLog

            summary = str(result.data if result.success else result.error)
            db = SessionLocal()
            try:
                db.add(AuditLog(
                    agent="commercial_ai",
                    tool=result.tool,
                    execution_id=result.execution_id,
                    status="SUCCESS" if result.success else "FAILED",
                    duration=round(time.perf_counter() - started_at, 4),
                    result_summary=summary[:500],
                ))
                db.commit()
            finally:
                db.close()
        except Exception:
            logging.getLogger(__name__).debug("Unable to persist MCP audit log", exc_info=True)
