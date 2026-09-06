from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Callable


class ToolInputValidationError(ValueError):
    """Raised when an agent-generated tool call does not match its contract."""


def validate_tool_arguments(arguments: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Small, dependency-free validator for the JSON-schema subset used by MCP tools.

    Tool contracts are generated into the planner prompt, but they must also be
    enforced at the execution boundary.  This intentionally supports only the
    constructs used in this project (objects, arrays, primitive types and enum).
    """
    if not isinstance(arguments, dict):
        raise ToolInputValidationError("Tool arguments must be an object")

    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in arguments or arguments[name] is None:
            raise ToolInputValidationError(f"Missing required argument: {name}")

    unknown = set(arguments) - set(properties)
    additional_properties = schema.get("additionalProperties", False)
    if unknown and additional_properties is False:
        raise ToolInputValidationError(f"Unsupported argument(s): {', '.join(sorted(unknown))}")
    if unknown and isinstance(additional_properties, dict):
        for name in unknown:
            # Validate map-like inputs such as product-code-to-quantity.
            value_schema = additional_properties
            expected = value_schema.get("type")
            if expected == "integer" and (not isinstance(arguments[name], int) or isinstance(arguments[name], bool)):
                raise ToolInputValidationError(f"{name} must be an integer")
            if expected == "string" and not isinstance(arguments[name], str):
                raise ToolInputValidationError(f"{name} must be a string")

    def validate_value(value: Any, value_schema: Dict[str, Any], path: str, parent: dict, key: str) -> None:
        if value is None:
            return
        expected = value_schema.get("type")
        
        # Implicit coercion for array when string is provided
        if expected == "array" and isinstance(value, str):
            if not value.strip() or value.strip().lower() == "none" or value.strip() == "[]":
                value = []
                parent[key] = value
            else:
                # Try parsing as JSON list, otherwise wrap in list
                import json
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        value = parsed
                    else:
                        value = [value]
                except json.JSONDecodeError:
                    value = [value]
                parent[key] = value

        # Implicit coercion for integer/number when string is provided
        if expected in ("integer", "number") and isinstance(value, str):
            try:
                if expected == "integer":
                    value = int(value)
                else:
                    value = float(value)
                parent[key] = value
            except (ValueError, TypeError):
                pass # let the validator fail later
                
        valid = {
            "string": isinstance(value, str),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "array": isinstance(value, list),
            "object": isinstance(value, dict),
        }
        if expected and not valid.get(expected, True):
            raise ToolInputValidationError(f"{path} must be a {expected}")
        if "enum" in value_schema and value not in value_schema["enum"]:
            raise ToolInputValidationError(f"{path} must be one of {value_schema['enum']}")
        if isinstance(value, str):
            if "minLength" in value_schema and len(value) < value_schema["minLength"]:
                raise ToolInputValidationError(f"{path} is shorter than the minimum length")
            if "maxLength" in value_schema and len(value) > value_schema["maxLength"]:
                raise ToolInputValidationError(f"{path} exceeds the maximum length")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in value_schema and value < value_schema["minimum"]:
                raise ToolInputValidationError(f"{path} must be at least {value_schema['minimum']}")
            if "maximum" in value_schema and value > value_schema["maximum"]:
                raise ToolInputValidationError(f"{path} must be at most {value_schema['maximum']}")
        if expected == "array":
            if "minItems" in value_schema and len(value) < value_schema["minItems"]:
                raise ToolInputValidationError(f"{path} must contain at least {value_schema['minItems']} item(s)")
            if "maxItems" in value_schema and len(value) > value_schema["maxItems"]:
                raise ToolInputValidationError(f"{path} must contain at most {value_schema['maxItems']} item(s)")
            item_schema = value_schema.get("items", {})
            for index, item in enumerate(value):
                # Note: nested coercion not strictly required, passing a dummy dict/key for now
                dummy = {str(index): item}
                validate_value(item, item_schema, f"{path}[{index}]", dummy, str(index))
                value[index] = dummy[str(index)]
        elif expected == "object":
            for k, nested_schema in value_schema.get("properties", {}).items():
                if k in value:
                    validate_value(value[k], nested_schema, f"{path}.{k}", value, k)

    for name, value in arguments.items():
        if name in properties:
            validate_value(value, properties[name], name, arguments, name)

class ToolParameter(BaseModel):
    type: str
    description: str
    required: bool = True

class ToolSchema(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: str = "low" # low, medium, high, critical
    requires_approval: bool = False
    required_permission: Optional[str] = None
    
    # Internal callback function for the execution engine to invoke
    handler: Optional[Callable] = None

class ToolResult(BaseModel):
    success: bool
    tool: str
    execution_id: str
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
