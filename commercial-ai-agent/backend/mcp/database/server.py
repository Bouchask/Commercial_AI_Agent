from backend.mcp.registry import registry
from backend.mcp.schemas import ToolSchema
from backend.mcp.database.tools import search_client, get_services

def register_database_tools():
    registry.register_tool(
        ToolSchema(
            name="db.search_client",
            description="Search for a client by name in the database.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name or partial name of the client to search for."}
                },
                "required": ["name"]
            },
            output_schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    }
                }
            },
            risk_level="low",
            requires_approval=False,
            handler=search_client
        )
    )

    registry.register_tool(
        ToolSchema(
            name="db.get_services",
            description="Retrieve services from the database, optionally filtering by codes.",
            input_schema={
                "type": "object",
                "properties": {
                    "codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of service codes to retrieve."
                    }
                }
            },
            output_schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "code": {"type": "string"},
                        "name": {"type": "string"},
                        "unit_price": {"type": "number"}
                    }
                }
            },
            risk_level="low",
            requires_approval=False,
            handler=get_services
        )
    )

    from backend.mcp.database.tools import search_client, get_services, execute_sql_query, create_client, create_quote, get_quote, find_or_create_client, create_service, update_service_price, get_quote
    registry.register_tool(
        ToolSchema(
            name="db.create_quote",
            description="Create a quote in the database.",
            input_schema={
                "type": "object",
                "properties": {
                    "client_id": {"type": "integer"},
                    "items": {"type": "array", "items": {"type": "object"}},
                    "total_ht": {"type": "number"},
                    "total_tax": {"type": "number"},
                    "total_ttc": {"type": "number"},
                    "status": {"type": "string", "default": "draft"}
                },
                "required": ["client_id", "items", "total_ht", "total_tax", "total_ttc"]
            },
            output_schema={
                "type": "object",
                "additionalProperties": True
            },
            risk_level="medium",
            requires_approval=True,
            handler=create_quote
        )
    )

    registry.register_tool(
        ToolSchema(
            name="db.create_client",
            description="Create a new client in the database.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"}
                },
                "required": ["name"]
            },
            output_schema={
                "type": "object",
                "additionalProperties": True
            },
            risk_level="medium",
            requires_approval=True,
            handler=create_client
        )
    )

    registry.register_tool(
        ToolSchema(
            name="db.get_quote",
            description="Retrieve a stored quote with its totals and line items.",
            input_schema={"type": "object", "properties": {"quote_id": {"type": "integer"}}, "required": ["quote_id"]},
            output_schema={"type": "object", "additionalProperties": True},
            risk_level="low",
            requires_approval=False,
            handler=get_quote,
        )
    )

    registry.register_tool(
        ToolSchema(
            name="db.find_or_create_client",
            description="PREFERRED for client lookup. Searches for a client by name. If found, returns the existing client. If NOT found, automatically creates a new client. Always returns a single object with 'id', 'name', 'email'. Use this instead of db.search_client to guarantee you always get a client_id back.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Client name to find or create."},
                    "email": {"type": "string", "description": "Client email (used if creating new)."},
                    "phone": {"type": "string", "description": "Client phone (used if creating new)."},
                    "address": {"type": "string", "description": "Client address (used if creating new)."}
                },
                "required": ["name"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                }
            },
            risk_level="medium",
            requires_approval=True,
            handler=find_or_create_client
        )
    )

    registry.register_tool(
        ToolSchema(
            name="db.create_service",
            description="Create a new service in the catalogue with a specified name and price.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the service."},
                    "unit_price": {"type": "number", "description": "Unit price of the service."},
                    "description": {"type": "string", "description": "Optional description of the service."}
                },
                "required": ["name", "unit_price"]
            },
            output_schema={"type": "object", "additionalProperties": True},
            risk_level="medium",
            requires_approval=True,
            handler=create_service
        )
    )

    registry.register_tool(
        ToolSchema(
            name="db.update_service_price",
            description="Update the price of an existing service by ID or name.",
            input_schema={
                "type": "object",
                "properties": {
                    "service_identifier": {"type": ["integer", "string"], "description": "Service ID or exact name to update."},
                    "new_price": {"type": "number", "description": "New unit price for the service."}
                },
                "required": ["service_identifier", "new_price"]
            },
            output_schema={"type": "object", "additionalProperties": True},
            risk_level="medium",
            requires_approval=True,
            handler=update_service_price
        )
    )
