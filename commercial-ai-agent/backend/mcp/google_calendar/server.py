from backend.mcp.registry import registry
from backend.mcp.schemas import ToolSchema
from backend.mcp.google_calendar.tools import create_meeting, check_availability

def register_google_calendar_tools() -> None:
    registry.register_tool(
        ToolSchema(
            name="google.calendar.create_meeting",
            description="Create a meeting in the user's Google Calendar.",
            handler=create_meeting,
            requires_approval=True,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title or summary of the meeting."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "The start time of the meeting in ISO 8601 format (e.g., 2026-08-18T10:00:00Z)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Optional. The end time of the meeting in ISO 8601 format. If omitted, defaults to 30 minutes after start_time."
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional. A list of email addresses of attendees to invite."
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional. A detailed description or agenda for the meeting."
                    }
                },
                "required": ["title", "start_time"]
            },
            output_schema={}
        )
    )
    
    registry.register_tool(
        ToolSchema(
            name="google.calendar.schedule_meeting",
            description="Schedule a meeting in Google Calendar, automatically send invitations to attendees, and generate a video conference room active strictly during the selected meeting time window.",
            handler=create_meeting,
            requires_approval=True,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title or subject of the meeting."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "The start time of the meeting in ISO 8601 format (e.g., 2026-08-18T10:00:00Z)."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Optional. The end time of the meeting in ISO 8601 format. Defaults to 30 minutes after start_time."
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The list of attendee/client email addresses to receive calendar invitations."
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional. Agenda or details for the meeting."
                    }
                },
                "required": ["title", "start_time"]
            },
            output_schema={}
        )
    )
    
    registry.register_tool(
        ToolSchema(
            name="google.calendar.check_availability",
            description="Check the user's Google Calendar for existing events to find free slots. Returns a list of busy slots between date_start and date_end.",
            handler=check_availability,
            requires_approval=False,
            input_schema={
                "type": "object",
                "properties": {
                    "date_start": {
                        "type": "string",
                        "description": "Start datetime in ISO 8601 format to check from."
                    },
                    "date_end": {
                        "type": "string",
                        "description": "End datetime in ISO 8601 format to check until."
                    }
                },
                "required": ["date_start", "date_end"]
            },
            output_schema={}
        )
    )
