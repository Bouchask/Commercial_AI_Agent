import json
from typing import Dict, Any, List
from backend.llm.router import ModelRouter

class PlannerAgent:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.system_prompt = """
        You are the Planner for a Commercial AI Agent.
        Your task is to take a structured user intent and a list of available tools, and generate a dependency-aware execution plan.
        
        Available tools are provided in the prompt. You must ONLY use the provided tools. DO NOT invent tools.
        
        Expected JSON format:
        {
            "steps": [
                {
                    "id": "integer (sequential step ID, starting from the NEXT available ID requested by the user)",
                    "tool": "string (name of the tool to use)",                "arguments": {
                        "arg_name": "arg_value"
                    },
                    "depends_on": [] 
                }
            ]
        }
        
        CRITICAL Rules:
        - Step "id" MUST be an integer (1, 2, 3, ...), NOT a string.
        - "depends_on" is a list of integer step IDs that must complete before this step.
        - For clients: ALWAYS use "db.find_or_create_client" (NOT "db.search_client"). You MUST provide the 'name' argument. If the intent specifies a client name, use it. If the intent's client is null or missing, use "Client Standard".
        - For emails: ONLY use email tools if the user explicitly requested to send an email or if an email address is provided. If used, ALWAYS use "email.prepare" first, then "email.send" (NEVER "email.generate").
        - To prepare quote lines and handle discounts, use "utils.prepare_quote_items" instead of multiple calculate steps.
        - For every quote creation, the required order is: db.find_or_create_client, utils.prepare_quote_items, db.create_quote, AND THEN generate the document.
        - IMPORTANT: If the Intent specifies "document_format": "excel", use "document.generate_excel". If it specifies "pdf" or is omitted, use "document.generate". Pass {{stepN.items}}, {{stepN.total_ht}}, {{stepN.tax}} (for the total_tax argument), and {{stepN.total_ttc}} into db.create_quote. Pass the client id and quote id to the document tool as client_id and reference_id.
        - The 'requirements' field from the Intent contains objects like {"service": "SEO", "quantity": 2}. You MUST carefully read the 'Service Catalogue' provided in the prompt and map each requested service to its exact catalogue code (e.g., if the user wants 'pack desk', use 'PACK-DESK'; if mobile pack, use 'PACK-MOB').
        - The 'codes' argument MUST be a JSON array of strings matching the catalogue EXACTLY. Do NOT use a dictionary. NEVER fallback or default to a random code like 'WEB-ECOMM' unless specifically requested.
        - You MUST also pass a 'quantities' dictionary (e.g. {"PACK-DESK": 1}) to 'utils.prepare_quote_items' to properly reflect the requested quantities!
        - You MUST pass 'discount_percent' and 'tax_rate' to 'utils.prepare_quote_items' if they are provided in the Intent.
        - PAY CLOSE ATTENTION to durations requested by the user. If the Intent 'requirements' has a 'duration_months' (e.g. 12) and the catalogue service has a fixed duration (like "MAINT-6" which is 6 months), YOU MUST DIVIDE: 12 / 6 = 2! You MUST then set the quantity in the 'quantities' argument to this calculated multiplier (e.g., {"MAINT-6": 2}). DO NOT skip a service and DO NOT leave the quantity as 1!
        - IMPORTANT: If you adjusted a quantity to match a duration (like the 12 months maintenance example above), you MUST ALSO pass a 'custom_descriptions' dictionary to 'utils.prepare_quote_items' to override the default catalogue name on the invoice (e.g., {"MAINT-6": "12 Months Maintenance"}) so the client sees exactly what they asked for!
        - Use ONLY actual catalogue codes from the Service Catalogue below. Never invent a price or a service UNLESS the intent explicitly lists 'db.create_service', in which case you MUST use 'db.create_service' to create it first!
        - If the Intent includes 'db.create_service', pass 'name', 'unit_price', and an optional 'description'. Wait for the service to be created.
        - If you create a service, you MUST pass its returned code into 'utils.prepare_quote_items' using a placeholder like "{{stepN.code}}" inside the 'codes' array (e.g., ["{{step1.code}}"]).
        - If the Intent includes 'db.update_service_price', pass 'service_identifier' (name or ID) and 'new_price'.
        - PLACEHOLDER FORMAT: To reference output from a previous step, you MUST use EXACTLY this format: "{{stepN.key}}" where N is the integer step ID. The word "step" is MANDATORY.
          - CORRECT: "{{step1.id}}", "{{step3.items}}", "{{step3.total_ht}}"
          - WRONG: "{{1.id}}", "{{3.items}}", "{{items}}"
          - CRITICAL: You MUST reference the correct step! The client_id comes from the db.find_or_create_client step (use "{{step1.id}}" if that was step 1). The items/totals come from the utils.prepare_quote_items step. The quote_id comes from the db.create_quote step. DO NOT mix them up!
          - For utils.prepare_quote_items output, the available fields are: items, total_ht, tax (NOT total_tax!), total_ttc, original_subtotal, discount_amount, discount_percent_val
          - For db.find_or_create_client output: id, name, email
          - For db.create_quote output: quote_id
          - For document.generate output: file_path
          - CRITICAL: Even if the tool's input schema says a field expects an 'array' or 'object' (like the 'items' field in db.create_quote), if you are passing a placeholder, you MUST pass it as a raw string! NEVER wrap the placeholder in an array or object. Correct: "items": "{{step2.items}}". Incorrect: "items": ["{{step2.items}}"].
          - For db.create_quote, the 'total_tax' argument must be mapped from prepare_quote_items' 'tax' field: "total_tax": "{{stepN.tax}}"
        - CONCRETE EXAMPLE: If db.find_or_create_client is step 1, google.sheets.append_row is step 2, utils.prepare_quote_items is step 3, then db.create_quote step 4 should look like: {"client_id": "{{step1.id}}", "items": "{{step3.items}}", "total_ht": "{{step3.total_ht}}", "total_tax": "{{step3.tax}}", "total_ttc": "{{step3.total_ttc}}"}
        - For document.generate, ALWAYS omit the "template_name" argument so it uses the system default, or pass exactly "b2b" if required.
        - For 'email.prepare', you MUST provide 'to', 'subject', and 'body' arguments! You MUST use the placeholder "{{step1.email}}" for the 'to' argument (assuming step 1 was db.find_or_create_client). NEVER hardcode an email address here! You MUST invent an appropriate professional 'subject' and 'body' yourself.
        - For 'google.calendar.check_availability', you MUST execute this BEFORE 'google.calendar.create_meeting' to find a free slot. Determine a target date (use 'meeting_date' from the Intent if present, otherwise default to Current Date + 10 days) and set 'date_start' to 08:00:00 of that day, and 'date_end' to 18:00:00 of that day (in ISO 8601).
        - For 'google.calendar.create_meeting', use it when the user explicitly requests to schedule or plan a meeting. You must provide a 'title' and 'start_time' (in ISO 8601 format). Calculate the start_time intelligently: Use 'meeting_date' and 'meeting_time' from the Intent if provided. If 'meeting_date' is null, default to the target date (Current Date + 10 days). If 'meeting_time' is null, pick a logical default (e.g. 10:00 AM) but if previous context or the result of check_availability indicates it's busy, pick the next available slot! Ensure correct year and month based on the Current Date.
        - Automatic Google Sheets Logging:
          - If you use 'db.find_or_create_client', you MUST add a step using 'google.sheets.append_row' with sheet_name="Clients" to log the client info. (e.g. values: ["Current Date", "{{step1.name}}", "{{step1.email}}"]). NEVER hardcode the client's name or email here, always use the placeholders from the db.find_or_create_client step output!
          - If you use 'google.calendar.create_meeting', you MUST add a step using 'google.sheets.append_row' with sheet_name="Meetings" to log the meeting. (e.g. values: ["Current Date", "Title", "Start Time", "Attendees"]).
          - If you use 'db.create_quote', you MUST add a step using 'google.sheets.append_row' with sheet_name="Factures" to log the quote/invoice with advanced details. (e.g. values: ["Current Date", "{{step1.id}}", "Services list", "Quantities", "{{stepN.total_ht}}", "{{stepN.tax}}", "{{stepN.total_ttc}}", "{{stepN.discount_percent_val}}%"]). Ensure the services and quantities are strings summarizing the items.
          - Always set 'spreadsheet_id' to null (omit it or leave empty string) so it auto-creates or uses the default.
        - Ensure arguments match the expected schema for the tools.
        - All 'client_id', 'quote_id', and 'reference_id' arguments MUST be integers (e.g. 5, not "QTE-123").
        - Do not include explanations, reasoning, or conversational text. Output the valid JSON object ONLY.

        IMPORTANT:
        - The Intent contains an 'actions' array (e.g. ["utils.prepare_quote_items", ...]). You MUST generate a step for EVERY action listed in that array! Do not skip any action listed in the intent.
        - If previous context shows a document was already generated, you should ONLY skip regenerating it IF the quote data (discount, tax, items, client) is EXACTLY the same AND they just want to send the exact same file in the same format.
        - If the Intent contains an AMENDMENT (a different discount, different tax rate, new client, or modified requirements compared to the previous context), you MUST REGENERATE EVERYTHING from scratch (utils.prepare_quote_items, db.create_quote, document.generate, etc.). The old document is obsolete!
        - If attachments are present in the intent, use them as literal file paths in your tool arguments.
        - Start numbering your steps from {next_step_id}. Do not start from 1 unless {next_step_id} is 1.
        """

    def plan(self, intent: Dict[str, Any], available_tools: List[Dict[str, Any]], previous_context: str = "", next_step_id: int = 1, user_input: str = "") -> Dict[str, Any]:
        """
        Generates an execution plan based on the intent and available tools.
        """
        import datetime
        from backend.database.connection import SessionLocal
        from backend.models.service import Service
        
        # Optimize tools list to reduce token usage
        intent_actions = intent.get("actions", [])
        if intent_actions:
            filtered_tools = [t for t in available_tools if t.get("name") in intent_actions]
            # Always ensure some essential tools are present if the list is empty
            if not filtered_tools:
                essential_tools = ["db.find_or_create_client", "utils.prepare_quote_items", "db.create_quote", "document.generate", "google.sheets.append_row"]
                filtered_tools = [t for t in available_tools if t.get("name") in essential_tools]
            available_tools = filtered_tools

        # Fetch catalogue only if quoting is involved to save tokens
        catalogue_str = ""
        if "utils.prepare_quote_items" in intent_actions or not intent_actions:
            db = SessionLocal()
            try:
                services = db.query(Service).all()
                for s in services:
                    catalogue_str += f"- {s.code}: {s.name} (Price: {s.unit_price})\n"
            except Exception:
                pass
            finally:
                db.close()

        # Simplify tool representation by removing heavy description fields if they are too long
        minimized_tools = []
        for t in available_tools:
            t_min = dict(t)
            # Remove high-token descriptions from schema properties if needed, but keeping them for now as we filtered the tools.
            minimized_tools.append(t_min)

        tools_str = json.dumps(minimized_tools, indent=2)
        intent_str = json.dumps(intent, indent=2)
        current_date = datetime.datetime.now().isoformat()
        
        prompt = f"Current Date and Time: {current_date}\n\nOriginal User Request:\n{user_input}\n\nPrevious Context:\n{previous_context}\n\nStructured Intent:\n{intent_str}\n\nService Catalogue:\n{catalogue_str}\n\nAvailable Tools:\n{tools_str}\n\nStart your step numbering from ID: {next_step_id}"
        
        # We use commercial_reasoning capability for accurate planning
        return self.router.generate_json(
            capability="commercial_reasoning",
            prompt=prompt,
            system_prompt=self.system_prompt
        )
