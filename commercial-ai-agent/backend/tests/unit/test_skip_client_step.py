import pytest
from unittest.mock import MagicMock
from backend.mcp.database.tools import create_quote
from backend.agents.prompt_engineer import PromptEngineerAgent
from backend.agents.planner import PlannerAgent

def test_create_quote_without_client_id_assigns_default_client():
    from backend.models.base import Base
    from backend.database.connection import engine
    Base.metadata.create_all(bind=engine)
    try:
        items = [
            {
                "service_code": "PACK-WEB",
                "description": "Pack Web Starter",
                "quantity": 1,
                "unit_price": 5000.0,
                "total": 5000.0
            }
        ]
        # Call create_quote with client_id=None
        result = create_quote(
            items=items,
            total_ht=5000.0,
            total_tax=1000.0,
            total_ttc=6000.0,
            client_id=None
        )
        assert result is not None
        assert "quote_id" in result
        assert result.get("total_ttc") == 6000.0
    finally:
        pass

def test_prompt_engineer_prompt_does_not_instruct_default_client():
    mock_router = MagicMock()
    mock_router.generate_json.return_value = {
        "intent": "create_quote",
        "client": None,
        "actions": ["utils.prepare_quote_items", "db.create_quote", "document.generate"]
    }
    agent = PromptEngineerAgent(mock_router)
    res = agent.analyze("generate devis pour pack web avec maintenance et seo", user_info="boyahya643@gmail.com")
    
    # Verify the router was called
    assert mock_router.generate_json.called
    call_kwargs = mock_router.generate_json.call_args.kwargs
    prompt_sent = call_kwargs["prompt"]
    # Ensure "(Use this as default client if no client is specified)" is NOT in prompt
    assert "(Use this as default client if no client is specified)" not in prompt_sent
    assert res["client"] is None

def test_planner_plan_without_client():
    mock_router = MagicMock()
    mock_router.generate_json.return_value = {
        "steps": [
            {
                "id": 1,
                "tool": "utils.prepare_quote_items",
                "arguments": {"codes": ["PACK-WEB"]},
                "depends_on": []
            },
            {
                "id": 2,
                "tool": "db.create_quote",
                "arguments": {
                    "items": "{{step1.items}}",
                    "total_ht": "{{step1.total_ht}}",
                    "total_tax": "{{step1.tax}}",
                    "total_ttc": "{{step1.total_ttc}}"
                },
                "depends_on": [1]
            },
            {
                "id": 3,
                "tool": "document.generate",
                "arguments": {
                    "document_type": "quote",
                    "reference_id": "{{step2.quote_id}}",
                    "items": "{{step1.items}}",
                    "total_ht": "{{step1.total_ht}}",
                    "tax": "{{step1.tax}}",
                    "total_ttc": "{{step1.total_ttc}}"
                },
                "depends_on": [2]
            }
        ]
    }
    planner = PlannerAgent(mock_router)
    intent = {
        "intent": "create_quote",
        "client": None,
        "requirements": [{"service": "PACK-WEB", "quantity": 1}],
        "actions": ["utils.prepare_quote_items", "db.create_quote", "document.generate"]
    }
    available_tools = [
        {"name": "utils.prepare_quote_items"},
        {"name": "db.create_quote"},
        {"name": "document.generate"},
        {"name": "db.find_or_create_client"}
    ]
    plan = planner.plan(intent=intent, available_tools=available_tools, user_input="generate devis pour pack web")
    step_tools = [s["tool"] for s in plan["steps"]]
    assert "db.find_or_create_client" not in step_tools
    assert "db.create_quote" in step_tools
