import os
import json
import datetime
import dateutil.parser
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from backend.mcp.google_auth import get_user_google_credentials, get_current_user

def create_meeting(
    title: str, 
    start_time: str, 
    end_time: Optional[str] = None, 
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Create a Google Calendar meeting."""
    creds = get_user_google_credentials()
    if not creds:
        raise ValueError("User Google credentials not found. Please log in with Google.")
        
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Parse start time
        start_dt = dateutil.parser.parse(start_time)
        
        # Default duration to 30 minutes if not provided
        if not end_time:
            end_dt = start_dt + datetime.timedelta(minutes=30)
        else:
            end_dt = dateutil.parser.parse(end_time)
            
        event = {
            'summary': title,
            'description': description or '',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [{'email': email} for email in attendees] if attendees else [],
            'reminders': {
                'useDefault': True,
            },
        }

        # Attach Google Meet video conference
        import uuid
        request_id = f"meet-{uuid.uuid4().hex[:12]}"
        event['conferenceData'] = {
            'createRequest': {
                'requestId': request_id,
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        }

        try:
            event_result = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1,
                sendUpdates='all'
            ).execute()
        except Exception as conf_err:
            # Fallback if Google Workspace conferenceData is disabled or unavailable
            event.pop('conferenceData', None)
            event_result = service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'
            ).execute()
        
        html_link = event_result.get('htmlLink')
        
        # Multi-account fix: Append authuser to the link so the browser opens it with the correct account
        try:
            user = get_current_user()
            if user and user.email and html_link:
                join_char = '&' if '?' in html_link else '?'
                html_link = f"{html_link}{join_char}authuser={user.email}"
        except Exception:
            pass

        # Extract or generate video meeting room (Google Meet or secure room)
        meet_link = event_result.get('hangoutLink')
        if not meet_link:
            conf_data = event_result.get('conferenceData', {})
            entry_points = conf_data.get('entryPoints', [])
            for ep in entry_points:
                if ep.get('entryPointType') == 'video':
                    meet_link = ep.get('uri')
                    break

        meet_id = f"meet_{uuid.uuid4().hex[:10]}"
        if not meet_link:
            meet_link = f"https://meet.jit.si/CommercialMeet_{meet_id}"

        # Time-restricted window: Active strictly around the chosen meeting date/time
        # (15 minutes before start for arrival, up to 30 minutes after end)
        active_from = start_dt - datetime.timedelta(minutes=15)
        active_until = end_dt + datetime.timedelta(minutes=30)
        time_locked_room_url = f"/api/meet/{meet_id}"

        # Persist to PostgreSQL database for cross-request and cross-device availability
        try:
            from backend.database.connection import SessionLocal
            from backend.models.meeting import Meeting
            db = SessionLocal()
            try:
                meeting_record = Meeting(
                    id=meet_id,
                    title=title,
                    description=description,
                    start_time=start_dt,
                    end_time=end_dt,
                    active_from=active_from,
                    active_until=active_until,
                    attendees=json.dumps(attendees or []),
                    google_event_id=event_result.get('id'),
                    google_calendar_link=html_link,
                    meet_url=meet_link
                )
                db.add(meeting_record)
                db.commit()
            finally:
                db.close()
        except Exception as db_error:
            print(f"Warning: could not persist meeting to DB: {db_error}")
            
        # Save meeting info to client folder if possible
        try:
            # We assume the first attendee is the primary client, or we try to guess the client name
            if attendees:
                client_email = attendees[0]
                client_name = client_email.split('@')[0] # Fallback name
                safe_client_name = "".join([c for c in client_name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
                safe_client_email = "".join([c for c in client_email if c.isalnum() or c in ('@', '.', '-', '_')]).strip()
                client_folder_name = f"{safe_client_name}_{safe_client_email}"
                
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                meet_dir = os.path.join(base_dir, "data", "clients", client_folder_name, "meet")
                os.makedirs(meet_dir, exist_ok=True)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"meet_{timestamp}.json"
                filepath = os.path.join(meet_dir, filename)
                
                with open(filepath, "w") as f:
                    json.dump({
                        "id": meet_id,
                        "title": title,
                        "description": description,
                        "start_time": start_time,
                        "end_time": end_dt.isoformat(),
                        "active_from": active_from.isoformat(),
                        "active_until": active_until.isoformat(),
                        "attendees": attendees,
                        "event_id": event_result.get('id'),
                        "calendar_link": html_link,
                        "meet_url": meet_link,
                        "time_locked_room_url": time_locked_room_url
                    }, f, indent=4)
        except Exception as file_error:
            print(f"Failed to save meeting file to client folder: {file_error}")
            
        return {
            "status": "success",
            "message": "Meeting created in calendar, video room generated, and invitations sent to attendee(s)",
            "meeting_id": meet_id,
            "event_id": event_result.get('id'),
            "calendar_link": html_link,
            "link": html_link,
            "meet_url": meet_link,
            "time_locked_room_url": time_locked_room_url,
            "title": title,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "active_from": active_from.isoformat(),
            "active_until": active_until.isoformat(),
            "attendees": attendees or [],
            "invitations_sent": True
        }
    except Exception as e:
        raise RuntimeError(f"Failed to create Google Calendar meeting: {str(e)}")

# Alias for explicit scheduling semantics
schedule_meeting = create_meeting

def check_availability(date_start: str, date_end: str) -> Dict[str, Any]:
    """
    Check Google Calendar availability by fetching events within a given time range.
    Returns a list of busy periods.
    """
    creds = get_user_google_credentials()
    if not creds:
        raise ValueError("User Google credentials not found. Please log in with Google.")
        
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Parse inputs
        start_dt = dateutil.parser.parse(date_start)
        end_dt = dateutil.parser.parse(date_end)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        busy_slots = []
        for event in events:
            # Skip all-day events which only have 'date' not 'dateTime'
            if 'dateTime' in event['start']:
                busy_slots.append({
                    "summary": event.get("summary", "Busy"),
                    "start": event['start']['dateTime'],
                    "end": event['end']['dateTime']
                })
                
        return {
            "status": "success",
            "timeMin": start_dt.isoformat(),
            "timeMax": end_dt.isoformat(),
            "busy_slots": busy_slots
        }
    except Exception as e:
        raise RuntimeError(f"Failed to check availability: {str(e)}")
