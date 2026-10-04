import json
from typing import Dict, Any, List
from backend.llm.router import ModelRouter

class PlannerAgent:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.system_prompt = """You are the Planner for a Commercial AI Agent.
Generate a dependency-aware JSON execution plan using ONLY the provided tools. Output raw JSON ONLY.

JSON Schema:
{
  "steps": [
    {
      "id": 1,
      "tool": "tool.name",
      "arguments": {"arg": "val"},
      "depends_on": []
    }
  ]
}

CRITICAL Rules:
1. Step "id" MUST be an integer (1, 2, ...), NOT a string. Number from next_step_id.
2. "depends_on": list of integer step IDs that must complete first.
3. Client step: ONLY use "db.find_or_create_client" if 'client' name is explicitly provided in the Intent or in 'actions'. If client is null or empty, SKIP IT completely! Never invent dummy client names like "Client Standard".
4. Quote / Invoice pipeline:
   - With client: db.find_or_create_client (1) -> utils.prepare_quote_items (2) -> db.create_quote (3, client_id="{{step1.id}}", items="{{step2.items}}", total_ht="{{step2.total_ht}}", total_tax="{{step2.tax}}", total_ttc="{{step2.total_ttc}}") -> document.generate (4, document_type="quote"|"invoice", reference_id="{{step3.quote_id}}", client_id="{{step1.id}}") -> google.sheets.append_row (5).
   - Without client: utils.prepare_quote_items (1) -> db.create_quote (2, items="{{step1.items}}", total_ht="{{step1.total_ht}}", total_tax="{{step1.tax}}", total_ttc="{{step1.total_ttc}}") -> document.generate (3, document_type="quote"|"invoice", reference_id="{{step2.quote_id}}") -> google.sheets.append_row (4).
5. Document type & Sheets:
   - Quote/Devis: document_type="quote", sheet_name="Devis". Values: ["Current Date", "Devis", "Services list", "Quantities", "{{stepN.total_ht}}", "{{stepN.tax}}", "{{stepN.total_ttc}}", "{{stepN.discount_percent_val}}%"].
   - Facture/Invoice: document_type="invoice", sheet_name="Factures". Values: ["Current Date", "Facture", ...].
   - If document_format="excel", use "document.generate_excel"; else "document.generate". Omit template_name or use "b2b".
6. Service mapping & items:
   - Map requirements to exact catalogue codes into 'codes' array (e.g. ["PACK-WEB", "MAINT-12", "SEO-OPT"]).
   - Pass 'quantities' dict (e.g. {"PACK-WEB": 1, "SEO-OPT": 1}).
   - If duration specified (e.g. 12 months with 6-month pack MAINT-6): divide 12/6 = 2, set qty=2, and pass custom_descriptions: {"MAINT-6": "12 Months Maintenance"}.
   - Pass 'discount_percent' and 'tax_rate' to utils.prepare_quote_items if present in intent.
   - If intent has 'db.create_service', run it first and pass "{{stepN.code}}" into 'codes'.
7. Placeholders:
   - Exact format: "{{stepN.key}}" (e.g. "{{step1.id}}", "{{step2.items}}", "{{step2.total_ht}}", "{{step2.tax}}", "{{step2.total_ttc}}", "{{step3.quote_id}}", "{{step4.file_path}}", "{{step1.email}}").
   - Always pass placeholders as plain strings, even for arrays/objects (e.g. "items": "{{step2.items}}").
8. QUOTE GENERATION OR AMENDMENT WITH EMAIL SENDING:
   - If sending existing/new quote to named client: step 1 is db.find_or_create_client (to get real email), then email.prepare ("to": "{{step1.email}}", "attachments": ["{{stepN.file_path}}"]), then email.send. Never fake emails.
   - If plan generates a document and sends email: attachments MUST be ["{{stepN.file_path}}"] referencing the newly generated document.
9. Calendar & Meetings:
   - check_availability -> create_meeting (title, start_time ISO, attendees) -> append_row (sheet_name="Meetings").
   - If client attendees specified: add email.prepare and email.send for each attendee depending on create_meeting step, with link "{{stepN.link}}".
10. All action items from Intent 'actions' MUST be included in the plan. Return JSON object ONLY."""

    def plan(self, intent: Dict[str, Any], available_tools: List[Dict[str, Any]], previous_context: str = "", next_step_id: int = 1, user_input: str = "") -> Dict[str, Any]:
        """
        Generates an execution plan based on the intent and available tools.
        """
        import datetime
        from backend.database.connection import SessionLocal
        from backend.models.service import Service
        
        # 1. Smart tool filtering to stay well under token limits
        intent_actions = intent.get("actions", [])
        if intent_actions:
            tools_to_include = set(intent_actions)
            if intent.get("client"):
                tools_to_include.add("db.find_or_create_client")
            filtered_tools = [t for t in available_tools if t.get("name") in tools_to_include]
            if not filtered_tools:
                essential_tools = [
                    "db.find_or_create_client", "utils.prepare_quote_items", "db.create_quote",
                    "document.generate", "google.sheets.append_row"
                ]
                filtered_tools = [t for t in available_tools if t.get("name") in essential_tools]
            available_tools = filtered_tools
        else:
            intent_name = intent.get("intent", "")
            if "quote" in intent_name or "invoice" in intent_name or intent.get("requirements"):
                candidate_names = {"utils.prepare_quote_items", "db.create_quote", "document.generate", "document.generate_excel", "google.sheets.append_row"}
                if intent.get("client"):
                    candidate_names.add("db.find_or_create_client")
                available_tools = [t for t in available_tools if t.get("name") in candidate_names]
            elif "meeting" in intent_name or intent.get("meeting_date"):
                candidate_names = {"google.calendar.check_availability", "google.calendar.create_meeting", "google.sheets.append_row", "email.prepare", "email.send"}
                available_tools = [t for t in available_tools if t.get("name") in candidate_names]
            else:
                candidate_names = {"db.find_or_create_client", "utils.prepare_quote_items", "db.create_quote", "document.generate", "google.sheets.append_row"}
                available_tools = [t for t in available_tools if t.get("name") in candidate_names]

        # 2. Compact catalogue representation
        catalogue_str = ""
        if "utils.prepare_quote_items" in intent_actions or not intent_actions or intent.get("requirements"):
            db = SessionLocal()
            try:
                services = db.query(Service).all()
                catalogue_lines = [f"{s.code}: {s.name} ({s.unit_price} MAD)" for s in services]
                catalogue_str = "; ".join(catalogue_lines)
            except Exception:
                pass
            finally:
                db.close()

        # 3. Compact tool schema representation (removes verbose schema boilerplate)
        minimized_tools = []
        for t in available_tools:
            schema = t.get("input_schema", {})
            props = schema.get("properties", {})
            req = schema.get("required", [])
            params = {}
            for p_name, p_info in props.items():
                p_type = p_info.get("type", "string")
                desc = p_info.get("description", "")
                if desc and len(desc) > 40:
                    desc = desc[:37] + "..."
                params[p_name] = f"{p_type}: {desc}" if desc else p_type
            minimized_tools.append({
                "name": t.get("name"),
                "desc": (t.get("description") or "").split(".")[0],
                "params": params,
                "required": req
            })

        tools_str = json.dumps(minimized_tools, separators=(',', ':'))
        intent_str = json.dumps(intent, separators=(',', ':'))
        current_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        prompt = f"Date: {current_date}\nRequest: {user_input}\nContext: {previous_context}\nIntent: {intent_str}\nCatalogue: {catalogue_str}\nTools: {tools_str}\nNext step ID: {next_step_id}"
        
        # We cap completion tokens to stay comfortably within Groq OTPM rate limits
        return self.router.generate_json(
            capability="commercial_reasoning",
            prompt=prompt,
            system_prompt=self.system_prompt,
            max_tokens=750
        )
