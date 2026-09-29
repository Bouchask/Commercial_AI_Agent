import pytest
from unittest.mock import MagicMock, patch
from backend.execution.executor_improved import ExecutionEngine
from backend.execution.state_machine import StateMachine, ExecutionState
from backend.agents.langgraph_orchestrator import LangGraphOrchestrator


class TestMeetingAndParallelInvitations:
    """Test scheduling meetings and sending invitations in parallel to 2 clients."""

    def test_meeting_with_two_client_invitations_executed_in_parallel(self):
        engine = ExecutionEngine(MagicMock())
        executed_order = []

        def mock_invoke(tool_name, arguments, execution_id=None):
            executed_order.append((tool_name, arguments.get("to")))
            if tool_name == "google.calendar.create_meeting":
                return {
                    "status": "success",
                    "event_id": "evt_12345",
                    "link": "https://calendar.google.com/event?eid=123",
                    "title": arguments.get("title"),
                    "start_time": arguments.get("start_time"),
                    "attendees": arguments.get("attendees"),
                }
            elif tool_name == "email.prepare":
                return {
                    "status": "prepared",
                    "to": arguments.get("to"),
                    "subject": arguments.get("subject"),
                    "body": arguments.get("body"),
                }
            return {"status": "ok"}

        engine.mcp.invoke = mock_invoke

        with patch.object(engine, "_validate_tool_result"):
            with patch("backend.execution.executor_improved.registry") as mock_reg:
                mock_tool = MagicMock()
                mock_tool.requires_approval = False
                mock_reg.get_tool.return_value = mock_tool

                sm = StateMachine()
                # Plan: Step 1 create meeting, Steps 2 & 3 send email to client1 and client2 in parallel
                plan = {
                    "steps": [
                        {
                            "id": 1,
                            "tool": "google.calendar.create_meeting",
                            "arguments": {
                                "title": "Réunion Cadrage Commercial",
                                "start_time": "2026-10-15T10:00:00Z",
                                "attendees": ["client1@acme.com", "client2@corp.org"],
                            },
                            "depends_on": [],
                        },
                        {
                            "id": 2,
                            "tool": "email.prepare",
                            "arguments": {
                                "to": "client1@acme.com",
                                "subject": "Invitation : Réunion Cadrage",
                                "body": "Rejoignez le meeting: {{step1.link}}",
                            },
                            "depends_on": [1],
                        },
                        {
                            "id": 3,
                            "tool": "email.prepare",
                            "arguments": {
                                "to": "client2@corp.org",
                                "subject": "Invitation : Réunion Cadrage",
                                "body": "Rejoignez le meeting: {{step1.link}}",
                            },
                            "depends_on": [1],
                        },
                    ]
                }

                result = engine.execute_plan("exec-meet-invites", plan, sm, approved_step_ids=[])

                assert result["status"] == "completed"
                assert sm.current_state == ExecutionState.COMPLETED
                assert len(result["results"]) == 3

                # Verify meeting was first
                assert executed_order[0][0] == "google.calendar.create_meeting"

                # Verify both emails were processed and interpolated the meeting link
                assert result["results"][2]["data"]["body"] == "Rejoignez le meeting: https://calendar.google.com/event?eid=123"
                assert result["results"][3]["data"]["body"] == "Rejoignez le meeting: https://calendar.google.com/event?eid=123"

                email_recipients = {executed_order[1][1], executed_order[2][1]}
                assert email_recipients == {"client1@acme.com", "client2@corp.org"}


class TestSelfHealingLoop:
    """Test the dynamic replanning (self-healing) node in the orchestrator."""

    def test_replan_node_adapts_plan_on_step_failure(self):
        orchestrator = LangGraphOrchestrator()

        # Mock PlannerAgent plan method to generate a healed plan
        orchestrator.planner.plan = MagicMock(return_value={
            "steps": [
                {
                    "id": 2,
                    "tool": "utils.calculate",
                    "arguments": {"expression": "200 + 50"},
                    "depends_on": [],
                }
            ]
        })

        initial_state = {
            "execution_id": "test-healing-001",
            "user_input": "Calculer le montant",
            "intent": {"actions": ["utils.calculate"]},
            "plan": {
                "steps": [
                    {"id": 1, "tool": "faulty_tool", "arguments": {}, "depends_on": []}
                ]
            },
            "results": {},
            "status": "need_replan",
            "replan_count": 1,
            "failed_step_info": {
                "step_id": 1,
                "tool": "faulty_tool",
                "error": "Temporary network timeout",
            },
        }

        repaired_state = orchestrator._node_replan(initial_state)

        assert repaired_state["status"] == "executing"
        assert len(repaired_state["plan"]["steps"]) == 1
        assert repaired_state["plan"]["steps"][0]["tool"] == "utils.calculate"
        orchestrator.planner.plan.assert_called_once()
        assert "SELF-HEALING" in orchestrator.planner.plan.call_args[1]["previous_context"]
