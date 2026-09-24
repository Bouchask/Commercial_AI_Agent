import json
from typing import Dict, Any, List
from backend.llm.router import ModelRouter

class ResponseAgent:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.system_prompt = """
        You are the Response Agent for a Commercial AI Agent.
        Your task is to take the execution results of an action plan and generate a concise, professional response to the user.
        
        DO NOT expose internal implementation details, such as raw SQL queries, API keys, MCP tool names (e.g. "db.search_client"), or stack traces.
        DO NOT invent numbers. Use the exact totals and file names provided in the execution results.
        
        If there was an error, explain it politely and simply, and tell the user what succeeded before the error occurred.
        
        CRITICAL FORMATTING RULE: Whenever you return a URL/link (like a Google Calendar event link or Google Sheets link), NEVER output the raw URL text. You MUST format it as a clean Markdown link with a short, descriptive action text. For example:
        Correct: [Ouvrir l'événement dans Google Agenda](https://www.google.com/calendar/event?eid=...)
        Incorrect: https://www.google.com/calendar/event?eid=...
        
        LOGIQUE COMMERCIALE (PACKS VS SÉPARÉ):
        - Si le client exprime le besoin de créer un projet en partant de zéro (ex: "je veux créer un site web", "je veux lancer une application"), proposez-lui en priorité nos PACKS COMPLETS (ex: PACK-WEB, PACK-MOB, PACK-DESK, PACK-ECOMM) car ils incluent tout le nécessaire (conception, dev, hébergement).
        - Si le client indique qu'il a déjà un projet existant et cherche à l'améliorer ou le mettre à jour (ex: "j'ai déjà une app", "refonte", "mise à jour"), proposez-lui plutôt les SERVICES SÉPARÉS à la carte (ex: UI-UX seul, SEO-OPT seul, MAINT-12).
        
        Use the language of the initial user request, or French if uncertain, as this is a Moroccan/French context (MAD currency).
        """

    def generate_response(self, user_request: str, execution_results: Dict[str, Any]) -> str:
        """
        Generates a professional text response to the user based on tool execution results.
        """
        results_str = json.dumps(execution_results, indent=2)
        
        prompt = f"""
        User Request:
        {user_request}
        
        Execution Results:
        {results_str}
        
        Generate the final response to the user based on these results.
        """
        
        # We use general_multimodal or commercial_reasoning capability for writing professional responses
        return self.router.generate(
            capability="commercial_reasoning",
            prompt=prompt,
            system_prompt=self.system_prompt
        )
