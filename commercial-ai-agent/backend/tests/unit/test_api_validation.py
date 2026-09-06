"""Smoke tests for the validated API factory.

These tests intentionally use only local SQLite and do not call an LLM,
email provider, or any external service.
"""


def test_health_reports_service_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["service"] == "commercial-ai-agent"
    assert payload["status"] in {"ok", "degraded"}
    assert "database" in payload


def test_login_rejects_non_json_payload(client):
    response = client.post("/api/login", data="not json", content_type="text/plain")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "INVALID_INPUT"


def test_process_requires_authentication(client):
    response = client.post("/api/process", json={"user_input": "Create a quote for Acme"})

    assert response.status_code == 401
