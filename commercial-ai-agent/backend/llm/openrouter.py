import json
import requests
from typing import Dict, Any, List, Optional
from backend.llm.base import LLMProvider
from backend.config.settings import settings

class OpenRouterProvider(LLMProvider):
    def __init__(self):
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.api_key = settings.OPENROUTER_API_KEY
        
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Commercial AI Agent"
        }

    def _make_request(self, payload: Dict[str, Any], timeout: float = 60.0) -> requests.Response:
        import time
        max_retries = 5
        for attempt in range(max_retries):
            response = requests.post(self.api_url, headers=self._headers(), json=payload, timeout=timeout)
            if response.status_code == 429 and attempt < max_retries - 1:
                # OpenRouter free tier rate limits, sleep longer and retry
                time.sleep(3 * (attempt + 1))
                continue
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    raise RuntimeError("OpenRouter API Error: Too Many Requests (429). You have hit the rate limit for your API key or the free tier. Please wait a moment and try again.")
                raise e
                
            return response
        return response

    def _extract_content(self, response: requests.Response) -> str:
        data = response.json()
        if "choices" not in data or not data["choices"]:
            error_msg = data.get("error", {}).get("message", "Unknown API Error")
            raise RuntimeError(f"OpenRouter API Error: {error_msg} (Full response: {data})")
        return data["choices"][0]["message"]["content"]

    def generate(self, prompt: str, model: str, system_prompt: Optional[str] = None, timeout: Optional[float] = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages
        }
        
        response = self._make_request(payload, timeout or 60.0)
        return self._extract_content(response)

    def generate_json(self, prompt: str, model: str, system_prompt: Optional[str] = None, timeout: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"}
        }
        
        response = self._make_request(payload, timeout or 60.0)
        raw = self._extract_content(response)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError("OpenRouter returned malformed JSON") from error

    def generate_with_tools(self, prompt: str, model: str, tools: List[Dict[str, Any]], system_prompt: Optional[str] = None, timeout: Optional[float] = None, **kwargs) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools
        }
        
        response = self._make_request(payload, timeout or 60.0)
        data = response.json()
        if "choices" not in data or not data["choices"]:
            error_msg = data.get("error", {}).get("message", "Unknown API Error")
            raise RuntimeError(f"OpenRouter API Error: {error_msg} (Full response: {data})")
        return data["choices"][0]["message"]

    def analyze_image(self, prompt: str, image_path: str, model: str, system_prompt: Optional[str] = None, timeout: Optional[float] = None, **kwargs) -> str:
        import base64
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode("ascii")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ]})
        response = self._make_request({"model": model, "messages": messages}, timeout or 60.0)
        return self._extract_content(response)
