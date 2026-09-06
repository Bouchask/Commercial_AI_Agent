import unittest
from unittest.mock import patch

from backend.execution.executor import ExecutionEngine
from backend.execution.state_machine import ExecutionState, StateMachine
from backend.mcp.client import MCPClient
from backend.mcp.registry import registry
from backend.mcp.schemas import ToolResult, ToolSchema
from backend.mcp.schemas import ToolInputValidationError, validate_tool_arguments
from backend.mcp.utils.tools import calculate
from backend.mcp.utils.tools import prepare_quote_items


class MCPBoundaryTests(unittest.TestCase):
    def setUp(self):
        registry._tools.clear()

    def tearDown(self):
        registry._tools.clear()

    def test_client_rejects_invalid_argument_type_before_handler_runs(self):
        called = []
        registry.register_tool(ToolSchema(
            name="test.echo",
            description="test",
            input_schema={"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]},
            output_schema={"type": "object"},
            handler=lambda count: called.append(count),
        ))

        result = MCPClient().execute_tool("test.echo", {"count": "not-an-integer"}, "execution")

        self.assertFalse(result.success)
        self.assertEqual(result.error["code"], "INVALID_TOOL_ARGUMENTS")
        self.assertEqual(called, [])

    def test_calculator_does_not_execute_python(self):
        self.assertEqual(calculate("(12 + 3) * 2")["result"], 30.0)
        with self.assertRaisesRegex(RuntimeError, "Only numeric arithmetic"):
            calculate("__import__('os').system('echo unsafe')")

    def test_schema_validator_enforces_bounds_before_tool_execution(self):
        schema = {
            "type": "object",
            "properties": {"discount": {"type": "number", "minimum": 0, "maximum": 1}},
            "required": ["discount"],
            "additionalProperties": False,
        }
        with self.assertRaisesRegex(ToolInputValidationError, "at most"):
            validate_tool_arguments({"discount": 1.5}, schema)
        with self.assertRaisesRegex(ToolInputValidationError, "Unsupported"):
            validate_tool_arguments({"discount": 0.2, "unexpected": True}, schema)

    def test_quote_item_aliases_resolve_to_catalogue_codes(self):
        catalogue = [
            {"id": 1, "code": "WEB-ECOMM", "name": "E-commerce Website", "unit_price": 5000.0, "tax_rate": 0.2},
            {"id": 3, "code": "SEO-OPT", "name": "SEO Optimization", "unit_price": 800.0, "tax_rate": 0.2},
        ]
        with patch("backend.mcp.database.tools.get_services", return_value=catalogue):
            result = prepare_quote_items(["ecommerce", "seo_optimization"])
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["service_id"], 1)
        self.assertEqual(result["total_ttc"], 6960.0)

    def test_resume_skips_completed_side_effects(self):
        calls = []

        def handler(name):
            calls.append(name)
            return {"name": name}

        registry.register_tool(ToolSchema(
            name="test.low",
            description="test",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            output_schema={"type": "object"},
            handler=handler,
        ))
        registry.register_tool(ToolSchema(
            name="test.approved",
            description="test",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            output_schema={"type": "object"},
            risk_level="high",
            requires_approval=True,
            handler=handler,
        ))
        plan = {"steps": [
            {"id": 1, "tool": "test.low", "arguments": {"name": "created-once"}, "depends_on": []},
            {"id": 2, "tool": "test.approved", "arguments": {"name": "sent-once"}, "depends_on": [1]},
        ]}
        engine = ExecutionEngine(MCPClient())
        state = StateMachine()

        paused = engine.execute_plan("execution", plan, state)
        self.assertEqual(state.current_state, ExecutionState.WAITING_APPROVAL)
        self.assertEqual(calls, ["created-once"])

        completed = engine.execute_plan(
            "execution", plan, state, approved_step_ids=[2], prior_results=paused["results_so_far"]
        )
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(calls, ["created-once", "sent-once"])


if __name__ == "__main__":
    unittest.main()
