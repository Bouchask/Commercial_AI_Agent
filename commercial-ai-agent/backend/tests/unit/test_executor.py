"""Tests for the execution engine: template resolution, plan validation, and step execution."""
import pytest
from unittest.mock import MagicMock, patch
from backend.execution.executor_improved import ExecutionEngine
from backend.execution.state_machine import StateMachine, ExecutionState


@pytest.fixture
def engine():
    mock_client = MagicMock()
    return ExecutionEngine(mock_client)


class TestPlanValidation:
    """Test plan structure validation."""

    def test_valid_plan(self, engine):
        plan = {"steps": [{"id": 1, "tool": "db.search_client", "arguments": {"name": "test"}}]}
        assert engine._validate_plan(plan) is None

    def test_empty_plan_is_valid(self, engine):
        plan = {"steps": []}
        assert engine._validate_plan(plan) is None

    def test_non_dict_plan_is_invalid(self, engine):
        assert engine._validate_plan("not a dict") is not None

    def test_duplicate_step_ids(self, engine):
        plan = {"steps": [{"id": 1, "tool": "a"}, {"id": 1, "tool": "b"}]}
        result = engine._validate_plan(plan)
        assert "Duplicate" in result

    def test_negative_step_id(self, engine):
        plan = {"steps": [{"id": -1, "tool": "a"}]}
        result = engine._validate_plan(plan)
        assert "positive" in result

    def test_self_dependency(self, engine):
        plan = {"steps": [{"id": 1, "tool": "a", "depends_on": [1]}]}
        result = engine._validate_plan(plan)
        assert "itself" in result

    def test_unknown_dependency(self, engine):
        plan = {"steps": [{"id": 1, "tool": "a", "depends_on": [99]}]}
        result = engine._validate_plan(plan)
        assert "unknown" in result


class TestTemplateResolution:
    """Test {{stepN.field}} template variable resolution."""

    def test_simple_substitution(self, engine):
        prior = {1: {"data": {"email": "test@example.com"}}}
        result = engine._substitute_templates("{{step1.email}}", prior)
        assert result == "test@example.com"

    def test_inline_substitution(self, engine):
        prior = {1: {"data": {"name": "John"}}}
        result = engine._substitute_templates("Hello {{step1.name}}!", prior)
        assert result == "Hello John!"

    def test_missing_step_returns_original(self, engine):
        prior = {}
        result = engine._substitute_templates("{{step99.email}}", prior)
        assert "step99" in str(result)

    def test_field_alias_tax(self, engine):
        prior = {1: {"data": {"tax": 1200.0}}}
        result = engine._substitute_templates("{{step1.total_tax}}", prior)
        assert result == 1200.0

    def test_raw_typed_value_preserved(self, engine):
        """When the entire value is a single placeholder, return the raw typed value."""
        prior = {1: {"data": {"id": 42}}}
        result = engine._substitute_templates("{{step1.id}}", prior)
        assert result == 42
        assert isinstance(result, int)

    def test_resolve_arguments_dict(self, engine):
        prior = {1: {"data": {"id": 5, "email": "a@b.com"}}}
        args = {"client_id": "{{step1.id}}", "to": "{{step1.email}}"}
        resolved = engine._resolve_arguments(args, prior)
        assert resolved["client_id"] == 5
        assert resolved["to"] == "a@b.com"


class TestExecutePlan:
    """Test full plan execution flow."""

    def test_completed_execution(self, engine):
        engine.mcp.invoke = MagicMock(return_value={"status": "ok"})
        with patch.object(engine, '_validate_tool_result'):
            with patch('backend.execution.executor_improved.registry') as mock_reg:
                mock_tool = MagicMock()
                mock_tool.requires_approval = False
                mock_reg.get_tool.return_value = mock_tool

                sm = StateMachine()
                plan = {"steps": [{"id": 1, "tool": "utils.calculate", "arguments": {"expression": "1+1"}}]}
                result = engine.execute_plan("test-123", plan, sm, approved_step_ids=[])

                assert result["status"] == "completed"
                assert sm.current_state == ExecutionState.COMPLETED

    def test_skips_already_completed_steps(self, engine):
        sm = StateMachine()
        prior = {1: {"success": True, "data": {"result": 42}}}
        plan = {"steps": [{"id": 1, "tool": "utils.calculate", "arguments": {}}]}
        result = engine.execute_plan("test-456", plan, sm, prior_results=prior)
        assert result["status"] == "completed"
        engine.mcp.invoke.assert_not_called()
