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


class TestMeetingRoomAndMCPTool:
    """Test the schedule_meeting MCP tool and time-locked room access control."""

    @patch("backend.mcp.google_calendar.tools.get_user_google_credentials")
    @patch("backend.mcp.google_calendar.tools.build")
    def test_create_meeting_mcp_tool_generates_timelocked_room_and_sends_invites(self, mock_build, mock_get_creds):
        from backend.mcp.google_calendar.tools import create_meeting, schedule_meeting
        
        mock_creds = MagicMock()
        mock_get_creds.return_value = mock_creds

        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_insert = MagicMock()
        mock_insert.execute.return_value = {
            "id": "gcal_evt_9988",
            "htmlLink": "https://calendar.google.com/event?eid=gcal_evt_9988",
            "hangoutLink": "https://meet.google.com/abc-defg-hij"
        }
        mock_events.insert.return_value = mock_insert
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service

        result = schedule_meeting(
            title="Point Stratégique & Offre Commerciale",
            start_time="2026-10-20T14:00:00Z",
            end_time="2026-10-20T15:00:00Z",
            attendees=["client@prospect.fr", "directeur@partner.com"],
            description="Présentation de la proposition"
        )

        assert result["status"] == "success"
        assert result["invitations_sent"] is True
        assert result["event_id"] == "gcal_evt_9988"
        assert result["meet_url"] == "https://meet.google.com/abc-defg-hij"
        assert result["time_locked_room_url"].startswith("/api/meet/meet_")
        assert "active_from" in result
        assert "active_until" in result

        # Verify Google Calendar API was called with sendUpdates='all' to dispatch invitations
        mock_events.insert.assert_called_once()
        call_kwargs = mock_events.insert.call_args[1]
        assert call_kwargs["sendUpdates"] == "all"
        assert call_kwargs["conferenceDataVersion"] == 1
        assert call_kwargs["body"]["attendees"] == [
            {"email": "client@prospect.fr"},
            {"email": "directeur@partner.com"}
        ]

    def test_time_locked_meeting_room_lifecycle(self, client):
        import datetime
        from backend.database.connection import SessionLocal
        from backend.models.meeting import Meeting

        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. Future meeting (Waiting Room state)
        future_meet_id = "test_meet_future_123"
        start_future = now + datetime.timedelta(hours=2)
        end_future = start_future + datetime.timedelta(minutes=45)
        
        # 2. Currently active meeting (Active Room state)
        active_meet_id = "test_meet_active_456"
        start_active = now - datetime.timedelta(minutes=10)
        end_active = now + datetime.timedelta(minutes=20)
        
        # 3. Past meeting (Expired Room state)
        past_meet_id = "test_meet_past_789"
        start_past = now - datetime.timedelta(days=1)
        end_past = start_past + datetime.timedelta(minutes=30)

        db = SessionLocal()
        try:
            # Seed the 3 meetings
            db.add(Meeting(
                id=future_meet_id,
                title="Future Session",
                start_time=start_future,
                end_time=end_future,
                active_from=start_future - datetime.timedelta(minutes=15),
                active_until=end_future + datetime.timedelta(minutes=30),
                meet_url="https://meet.google.com/future-room",
                attendees='["client@test.com"]'
            ))
            db.add(Meeting(
                id=active_meet_id,
                title="Active Live Session",
                start_time=start_active,
                end_time=end_active,
                active_from=start_active - datetime.timedelta(minutes=15),
                active_until=end_active + datetime.timedelta(minutes=30),
                meet_url="https://meet.google.com/active-live-room",
                attendees='["client@test.com"]'
            ))
            db.add(Meeting(
                id=past_meet_id,
                title="Past Completed Session",
                start_time=start_past,
                end_time=end_past,
                active_from=start_past - datetime.timedelta(minutes=15),
                active_until=end_past + datetime.timedelta(minutes=30),
                meet_url="https://meet.google.com/past-room",
                attendees='["client@test.com"]'
            ))
            db.commit()
        finally:
            db.close()

        # Test Case A: Future meeting JSON & HTML
        resp_future_json = client.get(f"/api/meet/{future_meet_id}?format=json")
        assert resp_future_json.status_code == 200
        data_future = resp_future_json.get_json()
        assert data_future["status"] == "waiting"
        assert data_future["active"] is False
        assert data_future["seconds_until_active"] > 0

        resp_future_html = client.get(f"/api/meet/{future_meet_id}")
        assert resp_future_html.status_code == 200
        assert b"Salle d'attente" in resp_future_html.data

        # Test Case B: Active meeting JSON & HTML
        resp_active_json = client.get(f"/api/meet/{active_meet_id}?format=json")
        assert resp_active_json.status_code == 200
        data_active = resp_active_json.get_json()
        assert data_active["status"] == "active"
        assert data_active["active"] is True
        assert data_active["meet_url"] == "https://meet.google.com/active-live-room"

        resp_active_html = client.get(f"/api/meet/{active_meet_id}")
        assert resp_active_html.status_code == 200
        assert b"active-live-room" in resp_active_html.data

        # Test Case C: Expired meeting JSON & HTML
        resp_past_json = client.get(f"/api/meet/{past_meet_id}?format=json")
        assert resp_past_json.status_code == 200
        data_past = resp_past_json.get_json()
        assert data_past["status"] == "expired"
        assert data_past["active"] is False

        resp_past_html = client.get(f"/api/meet/{past_meet_id}")
        assert resp_past_html.status_code == 200
        assert b"termin" in resp_past_html.data.lower()

        # Test Case D: Non-existent meeting
        resp_404 = client.get("/api/meet/non_existent_meet_id?format=json")
        assert resp_404.status_code == 404
