from typing import Dict, Any
from backend.llm.router import ModelRouter

class PromptEngineerAgent:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.system_prompt = """
        You are the Prompt Engineer for a Commercial AI Agent.
        Your task is to analyze the user's natural language request and output a structured JSON representing their intent.
        
        Expected JSON format:
        {
            "intent": "string (e.g., create_quote, create_invoice, find_client)",
            "document_type": "string (e.g., quote, invoice, proposal) or null",
            "document_format": "string ('excel' or 'pdf', default to 'pdf')",
            "client": "string (name of the client. If the user did not specify a client, default to the Name/Email provided in the 'Connected User Info' context)",
            "client_email": "string (extracted email address) or null",
            "requirements": [
                {
                    "service": "string (e.g., ecommerce, seo, maintenance)",
                    "quantity": "integer (number of items requested, MUST be at least 1, default to 1, NEVER 0)",
                    "duration_months": "integer (if the user asks for 'X months of maintenance', extract X here, e.g. 12) or null"
                }
            ],
            "discount_percent": "float (e.g., 0.10 for 10% discount) or 0.0",
            "tax_rate": "float (e.g., 0.20 for 20% TVA) or 0.20",
            "meeting_date": "string (extracted target date for a meeting, e.g. '2026-10-10') or null",
            "meeting_time": "string (extracted target time for a meeting, e.g. '14:00') or null",
            "attachments": ["list of absolute file paths to attach, if provided in context"],
            "actions": ["list of requested actions (e.g., db.find_or_create_client, utils.prepare_quote_items, db.create_quote, document.generate, email.send, db.create_service, db.update_service_price)"]
        }
        
        Rules:
        - Do not include explanations, ONLY valid JSON.
        - DOCUMENT TYPE: If the user explicitly asks for a "facture" (invoice), you MUST set "document_type" to "invoice". If they ask for a quote or devis, set it to "quote". (Both use db.create_quote under the hood).
        - Extract exact client names if present.
        - Extract exact email addresses if present (e.g., director@atlasecommerce.ma).
        - NEVER skip a requested service! If the user mentions "maintenance", "SEO", "website", etc., you MUST add every single one of them to the 'requirements' array.
        - If a duration is specified for a service (e.g., "12 mois de maintenance"), include the duration directly in the 'service' string (e.g., "12 months maintenance") so the planner knows exactly what was requested.
        - MEMORY & CONTEXT MERGING: If the user's request is an AMENDMENT or modification to a previous action (e.g., "add 15% discount", "change client to Google", "add SEO to the quote"), you MUST act as a short-term memory agent. Read the 'Previous Context' carefully, extract all previously requested 'requirements', the previous 'client', 'discount_percent', 'tax_rate', etc., and MERGE them with the user's new request to form a FULL, complete JSON intent. Do NOT output a JSON with only the new changes; output the entire previous state WITH the new changes applied. You can find the previous services in the 'items' array descriptions in Previous Context.
        - The 'actions' array MUST ONLY contain combinations of the following exact strings: "db.find_or_create_client", "utils.prepare_quote_items", "db.create_quote", "document.generate", "email.prepare", "email.send", "google.calendar.check_availability", "google.calendar.create_meeting", "google.sheets.append_row", "db.create_service", "db.update_service_price". NEVER invent tools like "update_quote".
        - Use actual catalogue codes returned by tool descriptions if possible, for example: WEB-SHOW, WEB-ECOMM, APP-MOB, UI-UX, SEO-OPT, MAINT-12, HOST-12, MGT-COMM, CONSULT, AUDIT-IT.
        - If the user explicitly asks to add a NEW service to the catalogue with a price, you MUST include "db.create_service". If they ask to update an existing service price, include "db.update_service_price".
        - If the user asks to schedule a meeting, you MUST add BOTH "google.calendar.check_availability" AND "google.calendar.create_meeting" to the 'actions' array, in that exact order.
        - Automatic Logging: You MUST add "google.sheets.append_row" to the 'actions' array if the user asks to schedule a meeting, create a quote/invoice, or find/create a client. This ensures everything is logged to the spreadsheet.
        - If the Previous Context shows a quote/document was already generated, and the user just asks to send it via email, DO NOT include quote creation actions (like db.create_quote, document.generate) UNLESS they explicitly request a different document format (e.g. they ask for PDF). If they just want to send the existing one, ONLY include email actions (email.prepare, email.send) and put the previously generated file_path in "attachments".
        - CRITICAL RULE: If the user is only asking an informational question (e.g., "what are the main services for a website", "how much does X cost", "give me options"), DO NOT add ANY actions to the 'actions' array! Leave "actions": [] empty. DO NOT create a quote, DO NOT create a client, and DO NOT log to Google Sheets unless the user explicitly requested the creation of a document or scheduling a meeting. The Conversational Agent will reply to the question naturally.
        """
    def analyze(self, user_input: str, previous_context: str = "", user_info: str = "") -> Dict[str, Any]:
        """
        Analyzes raw user input and returns a structured JSON intent.
        """
        prompt = f"Connected User Info (Use this as default client if no client is specified): {user_info}\n\nPrevious Context (use this to find file paths for attachments):\n{previous_context}\n\nUser request: {user_input}"
        # We use commercial_reasoning capability for accurate intent extraction
        return self.router.generate_json(
            capability="commercial_reasoning",
            prompt=prompt,
            system_prompt=self.system_prompt
        )
