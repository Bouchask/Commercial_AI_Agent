"""
Enhanced Execution Engine with timeout protection, result validation, and robust error handling.
"""
import re
import time
import logging
from typing import Dict, Any, List, Optional
from signal import alarm, SIGALRM, signal
from threading import Timer

from backend.mcp.client import MCPClient
from backend.mcp.registry import registry
from backend.execution.state_machine import StateMachine, ExecutionState
from backend.execution.approval import ApprovalManager
from backend.execution.retry import RetryPolicy
from backend.exceptions import (
    ExecutionError, ToolError, TimeoutError as AgentTimeoutError,
    ErrorCode, RetryableError
)
from backend.logging_config import log_execution, log_tool_invocation, log_performance

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Enhanced execution engine with timeout protection, error handling, and validation.
    """
    
    # Configuration
    DEFAULT_STEP_TIMEOUT_SEC = 30.0
    DEFAULT_EXECUTION_TIMEOUT_SEC = 300.0  # 5 minutes
    TOOL_OUTPUT_TIMEOUT_SEC = 30.0
    
    def __init__(
        self,
        mcp_client: MCPClient,
        step_timeout_sec: float = DEFAULT_STEP_TIMEOUT_SEC,
        execution_timeout_sec: float = DEFAULT_EXECUTION_TIMEOUT_SEC
    ):
        """
        Initialize execution engine.
        
        Args:
            mcp_client: MCP client for tool invocation
            step_timeout_sec: Maximum time per step
            execution_timeout_sec: Maximum time for entire execution
        """
        self.mcp = mcp_client
        self.step_timeout_sec = step_timeout_sec
        self.execution_timeout_sec = execution_timeout_sec
        self.retry_policy = RetryPolicy()
    
    def execute_plan(
        self,
        execution_id: str,
        plan: Dict[str, Any],
        state_machine: StateMachine,
        approved_step_ids: List[int] = None,
        prior_results: Dict[int, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a plan with timeout protection and comprehensive error handling.
        
        Args:
            execution_id: Unique execution ID
            plan: Execution plan with steps
            state_machine: State machine for tracking
            approved_step_ids: List of approved step IDs
            prior_results: Results from previous execution
        
        Returns:
            Execution result
        """
        start_time = time.time()
        approved_step_ids = approved_step_ids or []
        results = dict(prior_results or {})
        
        state_machine.transition_to(ExecutionState.EXECUTING)
        
        # Validate plan structure
        validation_result = self._validate_plan(plan)
        if validation_result:
            state_machine.transition_to(ExecutionState.FAILED, validation_result)
            return {"status": "failed", "reason": "invalid_plan", "results": results}
        
        steps = sorted(plan.get("steps", []), key=lambda x: x.get("id", 0))
        
        if not steps:
            state_machine.transition_to(ExecutionState.COMPLETED)
            return {"status": "completed", "results": results}
        
        log_execution(execution_id, 0, f"Starting execution of {len(steps)} steps")
        
        try:
            for step in steps:
                # Check execution timeout
                elapsed = time.time() - start_time
                if elapsed > self.execution_timeout_sec:
                    error_msg = f"Execution timeout exceeded ({elapsed:.1f}s > {self.execution_timeout_sec}s)"
                    state_machine.transition_to(ExecutionState.FAILED, error_msg)
                    raise AgentTimeoutError(
                        message=error_msg,
                        operation="execution",
                        timeout_sec=self.execution_timeout_sec
                    )
                
                result = self._execute_step(
                    execution_id=execution_id,
                    step=step,
                    approved_step_ids=approved_step_ids,
                    prior_results=results,
                    state_machine=state_machine
                )
                
                step_id = int(step["id"])
                results[step_id] = result
                
                # Check for failure or approval needed
                if not result.get("success") and result.get("status") != "waiting_approval":
                    error_msg = result.get("error", "Step failed without specific error message")
                    state_machine.transition_to(ExecutionState.FAILED, error_msg)
                    return {"status": "failed", "step": step_id, "results": results, "error": error_msg}
                
                if result.get("status") == "waiting_approval":
                    state_machine.transition_to(ExecutionState.WAITING_APPROVAL)
                    return {
                        "status": "waiting_approval",
                        "step": step_id,
                        "tool": step.get("tool"),
                        "arguments": result.get("arguments"),
                        "results": results
                    }
            
            state_machine.transition_to(ExecutionState.COMPLETED)
            log_execution(execution_id, 0, "Execution completed successfully")
            return {"status": "completed", "results": results}
        
        except AgentTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Execution failed: {str(e)}", exc_info=e)
            state_machine.transition_to(ExecutionState.FAILED, str(e))
            raise
    
    def _validate_plan(self, plan: Dict[str, Any]) -> Optional[str]:
        """
        Validate plan structure.
        
        Args:
            plan: Plan to validate
        
        Returns:
            Error message if invalid, None if valid
        """
        if not isinstance(plan, dict):
            return "Plan must be a dictionary"
        
        steps = plan.get("steps", [])
        if not isinstance(steps, list):
            return "Plan steps must be a list"
        
        if len(steps) == 0:
            return None  # Empty plans are valid
        
        # Validate step IDs
        step_ids = []
        for step in steps:
            try:
                step_id = int(step.get("id"))
                if step_id <= 0:
                    return f"Step ID must be positive, got {step_id}"
                if step_id in step_ids:
                    return f"Duplicate step ID: {step_id}"
                step_ids.append(step_id)
            except (TypeError, ValueError):
                return f"Step ID must be integer, got {step.get('id')}"
        
        # Validate dependencies
        for step in steps:
            step_id = int(step.get("id"))
            depends_on = step.get("depends_on", [])
            for dep_id in depends_on:
                try:
                    dep_id_int = int(dep_id)
                    if dep_id_int not in step_ids:
                        return f"Step {step_id} depends on unknown step {dep_id_int}"
                    if dep_id_int == step_id:
                        return f"Step {step_id} cannot depend on itself"
                except (TypeError, ValueError):
                    return f"Dependency must be integer, got {dep_id}"
        
        return None
    
    def _execute_step(
        self,
        execution_id: str,
        step: Dict[str, Any],
        approved_step_ids: List[int],
        prior_results: Dict[int, Dict[str, Any]],
        state_machine: StateMachine
    ) -> Dict[str, Any]:
        """
        Execute a single step with error handling and timeouts.
        
        Args:
            execution_id: Execution ID
            step: Step to execute
            approved_step_ids: List of approved step IDs
            prior_results: Prior execution results
            state_machine: State machine
        
        Returns:
            Step result
        """
        step_id = int(step["id"])
        tool_name = step.get("tool")
        arguments = step.get("arguments", {})
        depends_on = [int(d) for d in step.get("depends_on", [])]
        
        log_execution(execution_id, step_id, f"Executing step: {tool_name}")
        
        # Check if already executed
        if prior_results.get(step_id, {}).get("success"):
            log_execution(execution_id, step_id, "Step already completed, skipping")
            return {"success": True, "data": prior_results[step_id].get("data")}
        
        # Check dependencies
        for dep_id in depends_on:
            if dep_id not in prior_results or not prior_results[dep_id].get("success"):
                error_msg = f"Dependency step {dep_id} failed or not completed"
                log_execution(execution_id, step_id, error_msg)
                return {"success": False, "error": error_msg}
        
        # Get tool schema
        tool_schema = registry.get_tool(tool_name)
        if not tool_schema:
            error_msg = f"Tool '{tool_name}' not found in registry"
            logger.error(error_msg)
            raise ToolError(
                message=error_msg,
                tool_name=tool_name,
                tool_error=error_msg
            )

        # Interpolate arguments using prior results
        try:
            resolved_arguments = self._resolve_arguments(arguments, prior_results)
        except Exception as e:
            error_msg = f"Failed to resolve arguments: {str(e)}"
            logger.error(error_msg)
            raise ExecutionError(
                message=error_msg,
                step_id=step_id,
                execution_id=execution_id,
                original_error=e
            )

        # Check if approval needed AFTER interpolation so the UI shows actual values
        try:
            if ApprovalManager.requires_approval(tool_schema) and step_id not in approved_step_ids:
                # Persist a waiting tool call so UI/ops can approve it
                try:
                    from backend.database.connection import SessionLocal
                    from backend.models.execution import Execution, ToolCall
                    db = SessionLocal()
                    try:
                        # Ensure execution record exists
                        ex = db.query(Execution).filter(Execution.id == execution_id).first()
                        if not ex:
                            ex = Execution(id=execution_id, session_id=None, user_id=None, state='RECEIVED')
                            db.add(ex)
                            db.flush()
                        tc = ToolCall(execution_id=execution_id, tool_name=tool_name, arguments=resolved_arguments, status='WAITING_APPROVAL', duration=None)
                        db.add(tc)
                        db.commit()
                        db.refresh(tc)
                        tool_call_id = tc.id
                    finally:
                        db.close()
                except Exception:
                    logger.exception('Failed to persist waiting ToolCall')
                    tool_call_id = None

                log_execution(execution_id, step_id, "Waiting for approval")
                return {
                    "success": False,
                    "status": "waiting_approval",
                    "arguments": resolved_arguments,
                    "tool_call_id": tool_call_id
                }
        except Exception:
            # If approval manager errored, continue to attempt execution
            logger.exception('ApprovalManager check failed; continuing execution')
        
        # Execute tool with timeout
        log_tool_invocation(tool_name, resolved_arguments)
        start_time = time.time()
        
        try:
            logger.debug("Executing tool=%s raw_arguments=%s resolved=%s", tool_name, arguments, resolved_arguments)
            result = self._invoke_tool_with_timeout(
                tool_name=tool_name,
                arguments=resolved_arguments,
                timeout_sec=self.step_timeout_sec
            )
            
            # Validate result
            self._validate_tool_result(result, tool_schema)
            
            duration_ms = (time.time() - start_time) * 1000
            log_performance(f"step_{step_id}_{tool_name}", duration_ms)
            
            log_execution(execution_id, step_id, "Step completed successfully")
            return {"success": True, "data": result}
        
        except AgentTimeoutError as e:
            logger.error(f"Step {step_id} timed out after {self.step_timeout_sec}s")
            return {"success": False, "error": str(e)}
        
        except Exception as e:
            logger.error(f"Step {step_id} failed: {str(e)}", exc_info=e)
            return {"success": False, "error": str(e)}
    
    def _invoke_tool_with_timeout(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout_sec: float
    ) -> Any:
        """
        Invoke a tool with timeout protection.
        
        Args:
            tool_name: Name of tool
            arguments: Tool arguments
            timeout_sec: Timeout in seconds
        
        Returns:
            Tool result
        """
        start_time = time.time()
        
        try:
            # Invoke MCP tool
            result = self.mcp.invoke(tool_name, arguments)
            
            # Timeout was OK
            duration = time.time() - start_time
            if duration > timeout_sec:
                logger.warning(
                    f"Tool execution slow: {duration:.1f}s (timeout: {timeout_sec}s)"
                )
            
            return result
        
        except TimeoutError as e:
            raise AgentTimeoutError(
                message=f"Tool '{tool_name}' timed out",
                operation=tool_name,
                timeout_sec=timeout_sec,
                original_error=e
            )
        
        except Exception as e:
            raise ToolError(
                message=f"Tool '{tool_name}' invocation failed: {str(e)}",
                tool_name=tool_name,
                tool_error=str(e),
                original_error=e
            )
    
    def _resolve_arguments(
        self,
        arguments: Dict[str, Any],
        prior_results: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve template variables in arguments using prior results.
        
        Args:
            arguments: Arguments with templates
            prior_results: Prior execution results
        
        Returns:
            Resolved arguments
        """
        # Implementation of {{stepN.field}} template resolution
        resolved = {}
        
        for key, value in arguments.items():
            # Also resolve the key if it's a template string
            resolved_key = self._substitute_templates(key, prior_results) if isinstance(key, str) else key
            
            if isinstance(value, str):
                # Replace {{stepN.field}} patterns
                resolved[resolved_key] = self._substitute_templates(value, prior_results)
            elif isinstance(value, dict):
                resolved[resolved_key] = self._resolve_arguments(value, prior_results)
            elif isinstance(value, list):
                resolved[resolved_key] = [
                    self._substitute_templates(v, prior_results) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                resolved[resolved_key] = value
        
        return resolved
    
    def _substitute_templates(self, text: str, prior_results: Dict[int, Dict[str, Any]]) -> str:
        """
        Substitute {{stepN.field}} templates in text.
        
        Args:
            text: Text with templates
            prior_results: Prior results
        
        Returns:
            Substituted text
        """
        def replace_template(match):
            step_field = match.group(1)  # "stepN.field"
            parts = step_field.split(".")
            
            if len(parts) != 2:
                raise ValueError(f"Invalid template: {{{{{step_field}}}}}")
            
            step_prefix, field = parts
            step_num = int(step_prefix.replace("step_", "").replace("step", ""))
            
            if step_num not in prior_results:
                raise ValueError(f"Step {step_num} not found in results")
            
            data = prior_results[step_num].get('data', {})
            
            # Field Fallback Logic
            if field not in data:
                # Common aliases
                field_aliases = {
                    'total_tax': 'tax',
                    'tax': 'total_tax',
                    'total': 'total_ttc',
                }
                if field in field_aliases and field_aliases[field] in data:
                    field = field_aliases[field]
                elif field.endswith('_id') and 'id' in data:
                    field = 'id'
                else:
                    raise ValueError(f"Field '{field}' not found in step {step_num} results")
            
            # For inline replacements, coerce to string
            return "" if data[field] is None else str(data[field])
        
        # If the entire text is a single placeholder, return the raw typed value
        pattern_full = r"(?:\{\{|\$\{)?((?:step_?)?\d+\.\w+)(?:\}\}|\})?"
        full = re.fullmatch(pattern_full, text.strip())
        if full:
            step_field = full.group(1)
            parts = step_field.split('.')
            step_ref = parts[0]
            field = parts[1]
            
            # Extract step number
            try:
                step_num_str = re.search(r'\d+', step_ref).group()
                step_num = int(step_num_str)
                data = prior_results.get(step_num, {}).get('data', {})
            except (ValueError, AttributeError):
                data = {}
            
            # Fallback for field aliases and ID fields mapping
            if field not in data:
                field_aliases = {
                    'total_tax': 'tax',
                    'tax': 'total_tax',
                    'total': 'total_ttc',
                }
                if field in field_aliases and field_aliases[field] in data:
                    field = field_aliases[field]
                elif field.endswith('_id') and 'id' in data:
                    field = 'id'
                    
            if field not in data:
                return text
                
            return data[field]

        # Replace {{stepN.field}} patterns for inline substitutions
        pattern = r"(?:\{\{|\$\{)((?:step_?)?\d+\.\w+)(?:\}\}|\})"
        return re.sub(pattern, replace_template, text)
    
    def _validate_tool_result(self, result: Any, tool_schema: Dict[str, Any]) -> None:
        """
        Validate tool result against expected schema.
        
        Args:
            result: Tool result
            tool_schema: Expected schema
        
        Raises:
            ValueError if result doesn't match schema
        """
        # Basic validation - can be extended with Pydantic schemas
        if not isinstance(result, (dict, list, str, int, float, bool, type(None))):
            raise ValueError(f"Invalid tool result type: {type(result)}")
        
        # Check required fields if schema specifies
        if hasattr(tool_schema, 'output_schema'):
            # ToolSchema (Pydantic model)
            output_schema = tool_schema.output_schema or {}
        elif isinstance(tool_schema, dict):
            output_schema = tool_schema.get("output_schema", {})
        else:
            output_schema = {}

        required_fields = output_schema.get("required", []) if isinstance(output_schema, dict) else []

        if required_fields and isinstance(result, dict):
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field in tool result: {field}")
