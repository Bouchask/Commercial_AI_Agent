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

def test_generate_document_without_client_id_succeeds(monkeypatch):
    from backend.models.base import Base
    from backend.database.connection import engine
    from backend.mcp.document.tools import generate_document
    Base.metadata.create_all(bind=engine)
    
    # Mock compile_pdf and validate_pdf to avoid pdflatex dependencies in unit tests
    monkeypatch.setattr("backend.services.latex_service.LatexService.compile_pdf", lambda self, tex, doc_type: "/tmp/fake_quote.pdf")
    monkeypatch.setattr("backend.services.document_validation.DocumentValidator.validate_pdf", lambda path, ctx: (True, None))
    # Write a dummy byte to /tmp/fake_quote.pdf so it can be read
    with open("/tmp/fake_quote.pdf", "wb") as f:
        f.write(b"%PDF-1.4 dummy")

    result = generate_document(
        document_type="quote",
        items=[{"description": "Web Development", "quantity": 1, "price": 1000.0}],
        total_ht=1000.0,
        tax=200.0,
        total_ttc=1200.0,
        client_id=None,
        client_name=None,
        reference_id=None
    )
    assert result is not None
    assert result.get("success") is True
    assert result.get("document_id") is not None

def test_planner_includes_client_lookup_when_sending_email_to_named_client():
    mock_router = MagicMock()
    mock_router.generate_json.return_value = {
        "steps": [
            {
                "id": 1,
                "tool": "db.find_or_create_client",
                "arguments": {"name": "yahya qassifi"},
                "depends_on": []
            },
            {
                "id": 2,
                "tool": "email.prepare",
                "arguments": {
                    "to": "{{step1.email}}",
                    "subject": "Votre devis",
                    "body": "Bonjour Yahya...",
                    "attachments": ["data/quotes/quote_1.pdf"]
                },
                "depends_on": [1]
            },
            {
                "id": 3,
                "tool": "email.send",
                "arguments": {
                    "to": "{{step1.email}}",
                    "subject": "Votre devis",
                    "body": "Bonjour Yahya...",
                    "attachments": ["data/quotes/quote_1.pdf"]
                },
                "depends_on": [2]
            }
        ]
    }
    planner = PlannerAgent(mock_router)
    intent = {
        "intent": "send_email",
        "client": "yahya qassifi",
        "actions": ["email.prepare", "email.send"]
    }
    available_tools = [
        {"name": "utils.prepare_quote_items"},
        {"name": "db.create_quote"},
        {"name": "document.generate"},
        {"name": "db.find_or_create_client"},
        {"name": "email.prepare"},
        {"name": "email.send"}
    ]
    plan = planner.plan(intent=intent, available_tools=available_tools, user_input="ok , envoyes devis a yahya qassifi")
    
    # Check that db.find_or_create_client was in the tools passed to the prompt
    assert mock_router.generate_json.called
    call_prompt = mock_router.generate_json.call_args.kwargs["prompt"]
    assert "db.find_or_create_client" in call_prompt
    step_tools = [s["tool"] for s in plan["steps"]]
    assert "db.find_or_create_client" in step_tools
    assert plan["steps"][1]["arguments"]["to"] == "{{step1.email}}"

def test_email_prepare_and_send_links_attachments_to_recipient_client(monkeypatch, tmp_path):
    from backend.models.base import Base
    from backend.database.connection import SessionLocal, engine
    from backend.models.client import Client
    from backend.models.document import Document
    from backend.models.quote import Quote
    from backend.mcp.email.tools import prepare_email
    import os

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create a client
        client = Client(name="Yahya Qassifi", email="mr.bouchakyahya@gmail.com")
        db.add(client)
        
        # Create another default client
        default_client = Client(name="Client", email=None)
        db.add(default_client)
        db.commit()
        db.refresh(client)
        db.refresh(default_client)

        # Create a quote assigned to default_client
        quote = Quote(
            quote_number="QTE-TEST1234",
            client_id=default_client.id,
            subtotal=1000.0,
            tax_total=200.0,
            total_amount=1200.0,
            status="DRAFT"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)

        # Create a dummy attachment file in the managed data folder
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        data_dir = os.path.join(project_root, "data")
        os.makedirs(data_dir, exist_ok=True)
        test_file = os.path.join(data_dir, "test_quote_attach.pdf")
        with open(test_file, "wb") as f:
            f.write(b"%PDF-1.4 test")

        # Create document record
        doc = Document(
            filename="test_quote_attach.pdf",
            filepath=test_file,
            document_type="quote",
            reference_id=quote.id,
            client_id=default_client.id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Run prepare_email with recipient mr.bouchakyahya@gmail.com
        res = prepare_email(
            to="mr.bouchakyahya@gmail.com",
            subject="Votre devis",
            body="Bonjour",
            attachments=[test_file]
        )
        assert res["status"] == "prepared"

        # Verify that doc and quote are now linked to Yahya (client.id)
        db.refresh(doc)
        db.refresh(quote)
        assert doc.client_id == client.id
        assert quote.client_id == client.id
    finally:
        db.close()
        if os.path.exists(test_file):
            os.remove(test_file)

def test_tax_rate_normalization_prevents_extreme_tax(monkeypatch):
    from backend.mcp.utils.tools import prepare_quote_items
    
    # Mock get_services to return a service with tax_rate=20.0 (percentage format)
    monkeypatch.setattr(
        "backend.mcp.database.tools.get_services",
        lambda codes=None: [{
            "id": 100,
            "code": "SRV-TEST",
            "name": "analyse bug",
            "unit_price": 4000.0,
            "tax_rate": 20.0  # as percentage
        }]
    )
    result = prepare_quote_items(codes=["SRV-TEST"], quantities={"SRV-TEST": 1}, discount_percent=0.15)
    # 4000 with 15% discount: subtotal HT = 3400.0
    assert result["total_ht"] == 3400.0
    # Tax should be 20% of 3400 = 680.0, NOT 68,000!
    assert round(result["tax"], 2) == 680.0
    assert round(result["total_ttc"], 2) == 4080.0

def test_planner_amendment_with_email_wires_new_document_attachment():
    mock_router = MagicMock()
    mock_router.generate_json.return_value = {
        "steps": [
            {
                "id": 1,
                "tool": "db.find_or_create_client",
                "arguments": {"name": "yahya qassif"},
                "depends_on": []
            },
            {
                "id": 2,
                "tool": "utils.prepare_quote_items",
                "arguments": {"codes": ["PACK-MOB", "MAINT-12"], "discount_percent": 0.15},
                "depends_on": []
            },
            {
                "id": 3,
                "tool": "db.create_quote",
                "arguments": {"client_id": "{{step1.id}}", "items": "{{step2.items}}", "total_ht": "{{step2.total_ht}}", "total_tax": "{{step2.tax}}", "total_ttc": "{{step2.total_ttc}}"},
                "depends_on": [1, 2]
            },
            {
                "id": 4,
                "tool": "document.generate",
                "arguments": {"document_type": "invoice", "reference_id": "{{step3.quote_id}}", "client_id": "{{step1.id}}", "items": "{{step2.items}}", "total_ht": "{{step2.total_ht}}", "tax": "{{step2.tax}}", "total_ttc": "{{step2.total_ttc}}"},
                "depends_on": [3]
            },
            {
                "id": 5,
                "tool": "email.prepare",
                "arguments": {"to": "{{step1.email}}", "subject": "Facture", "body": "Bonjour", "attachments": ["{{step4.file_path}}"]},
                "depends_on": [1, 4]
            },
            {
                "id": 6,
                "tool": "email.send",
                "arguments": {"to": "{{step1.email}}", "subject": "Facture", "body": "Bonjour", "attachments": ["{{step4.file_path}}"]},
                "depends_on": [5]
            }
        ]
    }
    planner = PlannerAgent(mock_router)
    intent = {
        "intent": "create_invoice",
        "document_type": "invoice",
        "client": "yahya qassif",
        "discount_percent": 0.15,
        "actions": ["db.find_or_create_client", "utils.prepare_quote_items", "db.create_quote", "document.generate", "email.prepare", "email.send"]
    }
    available_tools = [
        {"name": "utils.prepare_quote_items"},
        {"name": "db.create_quote"},
        {"name": "document.generate"},
        {"name": "db.find_or_create_client"},
        {"name": "email.prepare"},
        {"name": "email.send"}
    ]
    plan = planner.plan(intent=intent, available_tools=available_tools, user_input="ajoute une remise de 15% a devis et envoye facteur a yahya qassif")
    
    # Check that prompt contains QUOTE GENERATION OR AMENDMENT WITH EMAIL SENDING instructions
    call_prompt = mock_router.generate_json.call_args.kwargs["prompt"]
    assert "QUOTE GENERATION OR AMENDMENT WITH EMAIL SENDING" in planner.system_prompt
    step_tools = [s["tool"] for s in plan["steps"]]
    assert "utils.prepare_quote_items" in step_tools
    assert "document.generate" in step_tools
    assert "email.prepare" in step_tools
    assert plan["steps"][4]["arguments"]["attachments"] == ["{{step4.file_path}}"]


