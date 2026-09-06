from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from backend.mcp.google_auth import get_user_google_credentials
from flask import request
from backend.database.connection import SessionLocal

def append_row(
    values: List[Any], 
    spreadsheet_id: Optional[str] = None, 
    sheet_name: str = "Sheet1"
) -> Dict[str, Any]:
    """Append a row of data to a Google Sheet."""
    creds = get_user_google_credentials()
    if not creds:
        raise ValueError("User Google credentials not found. Please log in with Google.")
        
    try:
        service = build('sheets', 'v4', credentials=creds)
        
        # Determine which spreadsheet_id to use
        current_user = getattr(request, 'current_user', None)
        if (current_user and current_user.default_spreadsheet_id and spreadsheet_id
                and spreadsheet_id != current_user.default_spreadsheet_id):
            raise ValueError("Only the authenticated user's default spreadsheet may be modified.")
        
        if not spreadsheet_id:
            if not current_user:
                raise ValueError("Cannot auto-create spreadsheet: no current user found in request.")
                
            # If the user already has a default spreadsheet, use it
            if current_user.default_spreadsheet_id:
                spreadsheet_id = current_user.default_spreadsheet_id
            else:
                # Create a new spreadsheet
                spreadsheet = {
                    'properties': {
                        'title': 'Commercial AI - Exports'
                    }
                }
                spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
                spreadsheet_id = spreadsheet.get('spreadsheetId')
                
                # Save it to the database so it's reused
                db = SessionLocal()
                try:
                    # Refresh the user object in this session
                    from backend.models.user import User
                    db_user = db.query(User).filter(User.id == current_user.id).first()
                    if db_user:
                        db_user.default_spreadsheet_id = spreadsheet_id
                        db.commit()
                        # Update the current_user object so subsequent calls in the same request have it
                        current_user.default_spreadsheet_id = spreadsheet_id
                finally:
                    db.close()
        
        if not spreadsheet_id:
            raise ValueError("Failed to determine or create a spreadsheet_id.")
            
        # Fetch the actual name of the first sheet to avoid locale issues (e.g. 'Sheet1' vs 'Feuille 1')
        try:
            sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheet_metadata.get('sheets', [])
            
            sheet_id = None
            if sheet_name == "Sheet1" and sheets:
                sheet_name = sheets[0].get("properties", {}).get("title", "Sheet1")
                sheet_id = sheets[0].get("properties", {}).get("sheetId")
            else:
                # Check if the specific sheet_name exists
                sheet_exists = False
                for s in sheets:
                    if s.get("properties", {}).get("title") == sheet_name:
                        sheet_exists = True
                        sheet_id = s.get("properties", {}).get("sheetId")
                        break
                
                if not sheet_exists:
                    # Create the sheet
                    add_sheet_request = {
                        "requests": [
                            {
                                "addSheet": {
                                    "properties": {
                                        "title": sheet_name
                                    }
                                }
                            }
                        ]
                    }
                    res = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=add_sheet_request).execute()
                    try:
                        sheet_id = res['replies'][0]['addSheet']['properties']['sheetId']
                    except Exception:
                        pass
        except Exception as e:
            print(f"Warning checking/creating sheet {sheet_name}: {e}")
            pass # Fallback to whatever was provided
            
        # Clean up bad rows, check headers, and prevent duplicates
        try:
            range_name_full = f"'{sheet_name}'!A:Z"
            existing_data_res = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name_full
            ).execute()
            existing_data = existing_data_res.get('values', [])
            
            requests = []
            
            # Clean up bad rows
            for i in range(len(existing_data)-1, -1, -1):
                row = existing_data[i]
                is_bad = any(isinstance(cell, str) and ('{{' in cell or cell == 'Current Date' or cell == 'Current Date Logged Here' or cell == 'Current Date') for cell in row)
                if is_bad:
                    if sheet_id is not None:
                        requests.append({
                            "deleteDimension": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "ROWS",
                                    "startIndex": i,
                                    "endIndex": i + 1
                                }
                            }
                        })
                    existing_data.pop(i)
            
            if requests:
                service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests}).execute()
            
            # Add headers if empty
            if not existing_data:
                headers = []
                if sheet_name == "Clients":
                    headers = ["Date", "Nom", "Email"]
                elif sheet_name == "Factures":
                    headers = ["Date", "Client ID", "Services", "Quantités", "Total HT", "TVA", "Total TTC", "Remise (%)"]
                elif sheet_name == "Meetings":
                    headers = ["Date", "Titre", "Heure de début", "Invités"]
                else:
                    headers = ["Date", "Info 1", "Info 2"]
                
                service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id, 
                    range=f"'{sheet_name}'!A:A",
                    valueInputOption="USER_ENTERED", 
                    body={'values': [headers]}
                ).execute()
                existing_data.append(headers)

            # Prevent duplicate clients
            if sheet_name == "Clients" and len(values) >= 3:
                new_email = str(values[2]).strip().lower()
                for row in existing_data:
                    if len(row) >= 3 and str(row[2]).strip().lower() == new_email:
                        link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
                        if current_user and current_user.email: link += f"?authuser={current_user.email}"
                        return {
                            "status": "success",
                            "message": f"Client {new_email} already exists in Sheets, skipped append.",
                            "spreadsheet_id": spreadsheet_id,
                            "link": link
                        }
        except Exception as e:
            print(f"Error in data cleanup/checks for {sheet_name}: {e}")
                
        # Quote the sheet name in case it has spaces
        range_name = f"'{sheet_name}'!A:A"
        body = {
            'values': [values]
        }
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, 
            range=range_name,
            valueInputOption="USER_ENTERED", 
            body=body
        ).execute()
        
        link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        try:
            if current_user and current_user.email:
                link = f"{link}?authuser={current_user.email}"
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Row appended successfully",
            "spreadsheet_id": spreadsheet_id,
            "link": link,
            "updatedRange": result.get('updates', {}).get('updatedRange')
        }
    except Exception as e:
        raise RuntimeError(f"Failed to append row to Google Sheet: {str(e)}")

def get_all_sheets_data(spreadsheet_id: str) -> Dict[str, List[List[Any]]]:
    """Fetch all data from a specific Google Sheet."""
    creds = get_user_google_credentials()
    if not creds:
        raise ValueError("User Google credentials not found.")
        
    try:
        service = build('sheets', 'v4', credentials=creds)
        
        # Get all sheet names
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        all_data = {}
        for sheet in sheets:
            title = sheet.get("properties", {}).get("title")
            if not title:
                continue
            
            # Fetch data for each sheet
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{title}'!A:Z"
            ).execute()
            
            all_data[title] = result.get('values', [])
            
        return all_data
    except Exception as e:
        raise RuntimeError(f"Failed to fetch data from Google Sheet: {str(e)}")
