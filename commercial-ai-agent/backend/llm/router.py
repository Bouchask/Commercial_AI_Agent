"""
LLM Model Router with intelligent capability-based model selection and error handling.
"""
import logging
import time
import inspect
import requests
from typing import Dict, Any, Optional, List
from backend.config.settings import settings
from backend.llm.base import LLMProvider
from backend.llm.ollama import OllamaProvider
from backend.llm.openrouter import OpenRouterProvider
from backend.llm.groq_provider import GroqProvider
from backend.exceptions import LLMError, TimeoutError as AgentTimeoutError, RetryableError, ErrorCode

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes requests to appropriate LLM providers and models based on capability."""
    
    def __init__(self, primary_provider: LLMProvider = None, timeout_sec: float = 300.0):
        """
        Initialize router with provider selection and configuration.
        
        Args:
            primary_provider: Override provider selection
            timeout_sec: Timeout for LLM calls in seconds
        """
        # Automatically use OpenRouter if an API key is provided
        if primary_provider:
            self.provider = primary_provider
            self.backup_provider = None
        elif settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
            self.provider = GroqProvider()
            import os
            self.backup_provider = OllamaProvider() if not os.environ.get("VERCEL") else None
        elif settings.OPENROUTER_API_KEY:
            self.provider = OpenRouterProvider()
            import os
            self.backup_provider = OllamaProvider() if not os.environ.get("VERCEL") else None
        else:
            self.provider = OllamaProvider()
            self.backup_provider = None
        
        self.timeout_sec = timeout_sec
        
        # Capability mapping based on settings
        self.capability_map = {
            "simple_extraction": settings.FAST_MODEL,
            "general_multimodal": settings.GENERAL_MODEL,
            "commercial_reasoning": settings.HEAVY_MODEL,
            "coding": settings.CODING_MODEL,
            "deep_reasoning": settings.REASONING_MODEL,
            "vision_specialist": settings.VISION_MODEL
        }
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay_sec = 1.0

    def get_model(self, capability: str, provider: Optional[LLMProvider] = None) -> str:
        """
        Get the specific model string for a given capability.
        
        Args:
            capability: Capability type
        
        Returns:
            Model name string
        """
        # Use the larger model for reasoning and the smaller model for cheap,
        # low-latency extraction.
        active_provider = provider or self.provider
        if isinstance(active_provider, GroqProvider):
            if capability == "simple_extraction":
                return settings.GROQ_FAST_MODEL
            return settings.GROQ_MODEL
            
        if capability in self.capability_map:
            return self.capability_map[capability]
        # Fallback to general model if capability not explicitly mapped
        logger.warning(f"Unknown capability '{capability}', using general model")
        return settings.GENERAL_MODEL

    def _call_with_retry(self, method_name: str, **kwargs) -> Any:
        """
        Call LLM method with retry logic and error handling.
        
        Args:
            method_name: Method to call (generate, generate_json, etc.)
            **kwargs: Arguments to pass to method
        
        Returns:
            Method result
        """
        last_error = None
        providers = [self.provider]
        if self.backup_provider is not None and self.backup_provider is not self.provider:
            providers.append(self.backup_provider)

        for attempt in range(self.max_retries):
            # Only try backup provider on the final attempt if it exists
            if attempt == self.max_retries - 1 and len(providers) > 1:
                provider = providers[1]
            else:
                provider = providers[0]
                
            call_kwargs = dict(kwargs)
            capability = call_kwargs.pop("_capability", None)
            if capability:
                call_kwargs["model"] = self.get_model(capability, provider)
            try:
                # Get method from provider
                method = getattr(provider, method_name)

                # Only add timeout if the provider method accepts it
                try:
                    sig = inspect.signature(method)
                    if 'timeout' in sig.parameters:
                        call_kwargs['timeout'] = self.timeout_sec
                except (ValueError, TypeError):
                    # If signature can't be inspected, fall back to not injecting timeout
                    pass

                logger.debug(
                    f"Calling {method_name} (attempt {attempt + 1}/{self.max_retries})",
                    extra={"extra_fields": {"method": method_name, "attempt": attempt + 1}}
                )
                
                # Call method
                result = method(**call_kwargs)
                
                logger.debug(f"Successfully called {method_name}")
                return result
            
            except (TimeoutError, requests.exceptions.Timeout) as e:
                last_error = e
                logger.warning(
                    f"LLM call timed out (attempt {attempt + 1})",
                    extra={"extra_fields": {"attempt": attempt + 1, "timeout_sec": self.timeout_sec}}
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_sec * (2 ** attempt))  # Exponential backoff
                else:
                    raise AgentTimeoutError(
                        message=f"LLM request timed out after {self.max_retries} attempts",
                        operation=method_name,
                        timeout_sec=self.timeout_sec,
                        original_error=e
                    )
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM call failed: {str(e)}",
                    extra={"extra_fields": {"attempt": attempt + 1, "error": str(e)}}
                )
                
                if attempt == 0 and len(providers) > 1:
                    logger.info("Primary LLM provider failed; trying fallback provider")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_sec * (2 ** attempt))
                else:
                    raise LLMError(
                        message=f"LLM request failed after {self.max_retries} attempts: {str(e)}",
                        error_code=ErrorCode.LLM_UNAVAILABLE,
                        model=call_kwargs.get("model"),
                        provider=type(provider).__name__,
                        original_error=e
                    )
        
        # Should not reach here, but just in case
        raise last_error or LLMError(
            message="LLM request failed for unknown reason",
            error_code=ErrorCode.LLM_UNAVAILABLE
        )

    def _call_capability(self, method_name: str, capability: str, **kwargs) -> Any:
        """Call a capability and keep model selection aligned with fallback providers."""
        kwargs["_capability"] = capability
        return self._call_with_retry(method_name, **kwargs)

    def generate(self, capability: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text response from LLM.
        
        Args:
            capability: Capability type
            prompt: User prompt
            system_prompt: System prompt
        
        Returns:
            Generated text
        """
        return self._call_capability(
            "generate",
            capability,
            prompt=prompt,
            system_prompt=system_prompt
        )

    def generate_json(self, capability: str, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate JSON response from LLM.
        
        Args:
            capability: Capability type
            prompt: User prompt
            system_prompt: System prompt
        
        Returns:
            Parsed JSON response
        """
        model = self.get_model(capability)
        try:
            result = self._call_capability(
                "generate_json",
                capability,
                prompt=prompt,
                system_prompt=system_prompt
            )
            
            # Validate result is dict
            if not isinstance(result, dict):
                raise LLMError(
                    message=f"Expected JSON response, got {type(result).__name__}",
                    error_code=ErrorCode.LLM_INVALID_RESPONSE,
                    model=model
                )
            
            return result
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(
                message=f"Failed to parse JSON response: {str(e)}",
                error_code=ErrorCode.LLM_INVALID_RESPONSE,
                model=model,
                original_error=e
            )

    def generate_with_tools(self, capability: str, prompt: str, tools: list, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate response with tool calling.
        
        Args:
            capability: Capability type
            prompt: User prompt
            tools: Available tools
            system_prompt: System prompt
        
        Returns:
            Response with tool calls
        """
        return self._call_capability(
            "generate_with_tools",
            capability,
            prompt=prompt,
            tools=tools,
            system_prompt=system_prompt
        )
        
    def analyze_image(self, capability: str, prompt: str, image_path: str, system_prompt: Optional[str] = None) -> str:
        """
        Analyze image with LLM.
        
        Args:
            capability: Capability type
            prompt: Analysis prompt
            image_path: Path to image file
            system_prompt: System prompt
        
        Returns:
            Analysis result
        """
        return self._call_capability(
            "analyze_image",
            capability,
            prompt=prompt,
            image_path=image_path,
            system_prompt=system_prompt
        )
