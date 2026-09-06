"""Contract tests for provider failover and timeout classification."""
import requests
import pytest

from backend.exceptions import TimeoutError as AgentTimeoutError
from backend.llm.base import LLMProvider
from backend.llm.router import ModelRouter


class RecordingProvider(LLMProvider):
    def __init__(self, response="ok", failure=None):
        self.response = response
        self.failure = failure
        self.calls = []

    def generate(self, prompt, model, system_prompt=None, timeout=None, **kwargs):
        self.calls.append({"prompt": prompt, "model": model, "timeout": timeout})
        if self.failure:
            raise self.failure
        return self.response

    def generate_json(self, *args, **kwargs):
        return {"ok": True}

    def generate_with_tools(self, *args, **kwargs):
        return {"tool_calls": []}

    def analyze_image(self, *args, **kwargs):
        return self.response


def test_router_uses_fallback_without_mutating_primary_provider():
    primary = RecordingProvider(failure=RuntimeError("provider unavailable"))
    fallback = RecordingProvider(response="fallback response")
    router = ModelRouter(primary_provider=primary, timeout_sec=12)
    router.backup_provider = fallback
    router.max_retries = 2
    router.retry_delay_sec = 0

    assert router.generate("simple_extraction", "hello") == "fallback response"
    assert router.provider is primary
    assert len(primary.calls) == 1
    assert fallback.calls == [{"prompt": "hello", "model": router.get_model("simple_extraction", fallback), "timeout": 12}]


def test_router_normalizes_transport_timeout():
    router = ModelRouter(primary_provider=RecordingProvider(failure=requests.exceptions.Timeout("slow")), timeout_sec=1)
    router.max_retries = 1

    with pytest.raises(AgentTimeoutError):
        router.generate("simple_extraction", "hello")
