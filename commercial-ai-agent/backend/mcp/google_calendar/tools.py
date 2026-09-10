import os
import json
import datetime
import dateutil.parser
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from backend.mcp.google_auth import get_user_google_credentials

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

        event_result = service.events().insert(calendarId='primary', body=event).execute()
        
        html_link = event_result.get('htmlLink')
        
        # Multi-account fix: Append authuser to the link so the browser opens it with the correct account
        try:
            from flask import request
            user = getattr(request, 'current_user', None)
            if user and user.email and html_link:
                join_char = '&' if '?' in html_link else '?'
                html_link = f"{html_link}{join_char}authuser={user.email}"
        except Exception:
            pass
            
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
                        "title": title,
                        "description": description,
                        "start_time": start_time,
                        "end_time": end_dt.isoformat(),
                        "attendees": attendees,
                        "event_id": event_result.get('id'),
                        "link": html_link
                    }, f, indent=4)
        except Exception as file_error:
            print(f"Failed to save meeting file to client folder: {file_error}")
            
        return {
            "status": "success",
            "message": "Meeting created successfully",
            "event_id": event_result.get('id'),
            "link": html_link
        }
    except Exception as e:
        raise RuntimeError(f"Failed to create Google Calendar meeting: {str(e)}")

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
