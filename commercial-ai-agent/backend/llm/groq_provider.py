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
        max_tokens = kwargs.pop('max_tokens', None) or kwargs.pop('max_completion_tokens', None) or settings.GROQ_MAX_COMPLETION_TOKENS
        # Groq on-demand tier caps OTPM at 1000. Keep max_completion_tokens comfortably under 900
        max_completion_tokens = min(int(max_tokens), 900)
        messages = self._format_messages(prompt, system_prompt)
        timeout = kwargs.pop('timeout', 120.0)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                reasoning_effort=settings.GROQ_REASONING_EFFORT,
                max_completion_tokens=max_completion_tokens,
                timeout=timeout
            )
            return self._content(response)
        except Exception as e:
            err_msg = str(e)
            if ("429" in err_msg or "OTPM" in err_msg or "reduce max_tokens" in err_msg) and max_completion_tokens > 350:
                logger.warning(f"Groq generate hit OTPM rate limit: {err_msg}. Retrying with 400 completion tokens...")
                import time
                time.sleep(1.5)
                try:
                    resp = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        reasoning_effort=settings.GROQ_REASONING_EFFORT,
                        max_completion_tokens=400,
                        timeout=timeout
                    )
                    return self._content(resp)
                except Exception:
                    pass
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
        max_tokens = kwargs.pop('max_tokens', None) or kwargs.pop('max_completion_tokens', None) or 750
        # Stay safely below 1000 OTPM for JSON outputs
        max_completion_tokens = min(int(max_tokens), 750)
        timeout = kwargs.pop('timeout', 120.0)

        json_system = "You must output a valid JSON object. Do not include markdown code blocks or explanations, just the raw JSON."
        if system_prompt:
            eff_system_prompt = f"{system_prompt}\n\n{json_system}"
        else:
            eff_system_prompt = json_system
            
        messages = self._format_messages(prompt, eff_system_prompt)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                # Qwen reasoning can consume the entire completion budget and
                # leave `content` empty. JSON extraction does not need it.
                reasoning_effort=settings.GROQ_JSON_REASONING_EFFORT,
                response_format={"type": "json_object"},
                temperature=0,
                max_completion_tokens=max_completion_tokens,
                timeout=timeout
            )
            
            content = self._content(response)
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
            err_msg = str(e)
            import time
            # Automatic mitigation for Groq OTPM (429) rate limit: retry with reduced completion tokens
            if ("429" in err_msg or "OTPM" in err_msg or "reduce max_tokens" in err_msg) and max_completion_tokens > 350:
                logger.warning(f"Groq OTPM rate limit hit ({err_msg}). Retrying with max_completion_tokens=350...")
                time.sleep(1.5)
                try:
                    retry_resp = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        reasoning_effort=settings.GROQ_JSON_REASONING_EFFORT,
                        response_format={"type": "json_object"},
                        temperature=0,
                        max_completion_tokens=350,
                        timeout=timeout
                    )
                    retry_content = self._content(retry_resp).strip()
                    if retry_content.startswith("```json"): retry_content = retry_content[7:]
                    elif retry_content.startswith("```"): retry_content = retry_content[3:]
                    if retry_content.endswith("```"): retry_content = retry_content[:-3]
                    return json.loads(retry_content.strip())
                except Exception as retry_err:
                    logger.error(f"Groq retry with 350 tokens also failed: {retry_err}")
            
            # Automatic mitigation for Groq ITPM (413) request too large: retry with compacted prompt
            elif ("413" in err_msg or "ITPM" in err_msg or "Request too large" in err_msg) and len(prompt) > 2000:
                logger.warning(f"Groq ITPM 413 limit hit. Retrying with compacted prompt...")
                time.sleep(1.0)
                try:
                    trimmed_prompt = prompt[:2000] + "\n[Context trimmed for token limit]"
                    trimmed_sys = eff_system_prompt[:1500] if eff_system_prompt else None
                    trimmed_msgs = self._format_messages(trimmed_prompt, trimmed_sys)
                    retry_resp = self.client.chat.completions.create(
                        model=model,
                        messages=trimmed_msgs,
                        reasoning_effort=settings.GROQ_JSON_REASONING_EFFORT,
                        response_format={"type": "json_object"},
                        temperature=0,
                        max_completion_tokens=350,
                        timeout=timeout
                    )
                    retry_content = self._content(retry_resp).strip()
                    if retry_content.startswith("```json"): retry_content = retry_content[7:]
                    elif retry_content.startswith("```"): retry_content = retry_content[3:]
                    if retry_content.endswith("```"): retry_content = retry_content[:-3]
                    return json.loads(retry_content.strip())
                except Exception as retry_err:
                    logger.error(f"Groq retry with compacted prompt failed: {retry_err}")

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
