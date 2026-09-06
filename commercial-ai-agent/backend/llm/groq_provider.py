import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from backend.config.settings import settings
from backend.llm.base import LLMProvider
from backend.exceptions import LLMError, ErrorCode

logger = logging.getLogger(__name__)

class GroqProvider(LLMProvider):
    """LLM Provider for Groq API using OpenAI compatible SDK."""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY must be set in settings or .env to use Groq provider")
        
        # Groq uses an OpenAI compatible API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        
    def _format_messages(self, prompt: str, system_prompt: Optional[str] = None) -> list:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    @staticmethod
    def _content(response) -> str:
        if not response.choices or not (content := response.choices[0].message.content):
            raise ValueError("Groq returned an empty completion")
        return content

    def generate(self, prompt: str, model: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text response using Groq API."""
        try:
            messages = self._format_messages(prompt, system_prompt)
            timeout = kwargs.pop('timeout', 120.0)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                reasoning_effort=settings.GROQ_REASONING_EFFORT,
                max_completion_tokens=settings.GROQ_MAX_COMPLETION_TOKENS,
                timeout=timeout
            )
            return self._content(response)
        except Exception as e:
            logger.error(f"Groq generate error: {str(e)}")
            raise LLMError(
                message=f"Groq generation failed: {str(e)}",
                error_code=ErrorCode.LLM_UNAVAILABLE,
                model=model,
                provider="GroqProvider",
                original_error=e
            )

    def generate_json(self, prompt: str, model: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate JSON response using Groq API."""
        content = ""
        try:
            json_system = "You must output a valid JSON object. Do not include markdown code blocks or explanations, just the raw JSON."
            if system_prompt:
                system_prompt = f"{system_prompt}\n\n{json_system}"
            else:
                system_prompt = json_system
                
            messages = self._format_messages(prompt, system_prompt)
            timeout = kwargs.pop('timeout', 120.0)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                # Qwen reasoning can consume the entire completion budget and
                # leave `content` empty. JSON extraction does not need it.
                reasoning_effort=settings.GROQ_JSON_REASONING_EFFORT,
                response_format={"type": "json_object"},
                temperature=0,
                max_completion_tokens=settings.GROQ_MAX_COMPLETION_TOKENS,
                timeout=timeout
            )
            
            content = self._content(response)
            
            # Clean markdown JSON block if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Groq JSON parse error: %s (response length=%d)", str(e), len(content))
            raise LLMError(
                message=f"Failed to parse Groq response as JSON: {str(e)}",
                error_code=ErrorCode.LLM_INVALID_RESPONSE,
                model=model,
                provider="GroqProvider",
                original_error=e
            )
        except Exception as e:
            logger.error(f"Groq generate_json error: {str(e)}")
            raise LLMError(
                message=f"Groq JSON generation failed: {str(e)}",
                error_code=ErrorCode.LLM_UNAVAILABLE,
                model=model,
                provider="GroqProvider",
                original_error=e
            )

    def generate_with_tools(self, prompt: str, tools: list, model: str, system_prompt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate response with tool calling using Groq API."""
        try:
            messages = self._format_messages(prompt, system_prompt)
            timeout = kwargs.pop('timeout', 120.0)
            
            formatted_tools = []
            for tool in tools:
                formatted_tools.append({
                    "type": "function",
                    "function": tool
                })
                
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=formatted_tools,
                tool_choice="auto",
                reasoning_effort=settings.GROQ_REASONING_EFFORT,
                max_completion_tokens=settings.GROQ_MAX_COMPLETION_TOKENS,
                timeout=timeout
            )
            
            message = response.choices[0].message
            
            result = {
                "content": message.content,
                "tool_calls": []
            }
            
            if message.tool_calls:
                for tc in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments or "{}")
                    })
                    
            return result
        except Exception as e:
            logger.error(f"Groq tool call error: {str(e)}")
            raise LLMError(
                message=f"Groq tool generation failed: {str(e)}",
                error_code=ErrorCode.LLM_UNAVAILABLE,
                model=model,
                provider="GroqProvider",
                original_error=e
            )

    def analyze_image(self, prompt: str, image_path: str, model: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Analyze image."""
        try:
            import base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
                
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            })
            
            timeout = kwargs.pop('timeout', 120.0)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=timeout
            )
            return self._content(response)
        except Exception as e:
            logger.error(f"Groq image analysis error: {str(e)}")
            raise LLMError(
                message=f"Groq image analysis failed: {str(e)}",
                error_code=ErrorCode.LLM_UNAVAILABLE,
                model=model,
                provider="GroqProvider",
                original_error=e
            )
