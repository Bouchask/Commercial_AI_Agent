from backend.mcp.registry import registry
from backend.mcp.schemas import ToolSchema
from backend.mcp.google_sheets.tools import append_row

def register_google_sheets_tools() -> None:
    registry.register_tool(
        ToolSchema(
            name="google.sheets.append_row",
            description="Append a row of data to a specific Google Spreadsheet.",
            handler=append_row,
            requires_approval=False,
            input_schema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "Optional. The ID of the Google Spreadsheet. If not provided, a default sheet will be automatically created or used."
                    },
                    "values": {
                        "type": "array",
                        "items": {},
                        "description": "An array of values to insert into the new row (e.g., ['Agile', 'Methodology used for fast iteration'])."
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional. The name of the sheet tab to append to. Defaults to 'Sheet1'."
                    }
                },
                "required": ["values"]
            },
            output_schema={}
        )
    )
