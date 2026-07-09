import json

import pytest
from pydantic import ValidationError

from src.core.llm.groq_client import call_groq_structured
from src.core.schemas import StrategyReport


@pytest.mark.asyncio
async def test_groq_validation_errors_are_not_retried_as_api_errors(monkeypatch):
    calls = []

    class FakeResponse:
        is_error = False
        status_code = 200
        text = ""

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"findings": "not a list"}),
                        }
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, *args, **kwargs):
            calls.append(kwargs["json"]["response_format"]["type"])
            return FakeResponse()

    monkeypatch.setattr(
        "src.core.llm.groq_client.httpx.AsyncClient",
        lambda timeout: FakeClient(),
    )

    with pytest.raises(ValidationError):
        await call_groq_structured(
            messages=[("system", "Return a report.")],
            schema=StrategyReport,
            model_name="test-model",
            api_key="test-key",
        )

    assert calls == ["json_schema"]


@pytest.mark.asyncio
async def test_qwen_uses_json_object_mode_without_json_schema_probe(monkeypatch):
    calls = []

    class FakeResponse:
        is_error = False
        status_code = 200
        text = ""

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "executive_summary": "Summary.",
                                    "findings": [],
                                    "market_analysis": [],
                                    "competitor_landscape": [],
                                    "technical_feasibility": [],
                                    "customer_validation": [],
                                    "opportunities": [],
                                    "risks": [],
                                    "recommendations": [],
                                    "kpis": [],
                                    "roadmap": [],
                                }
                            ),
                        }
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, *args, **kwargs):
            calls.append(kwargs["json"]["response_format"]["type"])
            return FakeResponse()

    monkeypatch.setattr(
        "src.core.llm.groq_client.httpx.AsyncClient",
        lambda timeout: FakeClient(),
    )

    result = await call_groq_structured(
        messages=[("system", "Return a report.")],
        schema=StrategyReport,
        model_name="qwen/qwen3-32b",
        api_key="test-key",
    )

    assert isinstance(result, StrategyReport)
    assert calls == ["json_object"]


@pytest.mark.asyncio
async def test_groq_json_schema_generation_error_falls_back_to_json_object(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self.payload = payload
            self.text = json.dumps(payload)
            self.is_error = status_code >= 400

        def json(self):
            return self.payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, *args, **kwargs):
            calls.append(kwargs["json"]["response_format"]["type"])
            if len(calls) == 1:
                return FakeResponse(
                    400,
                    {
                        "error": {
                            "message": "Failed to validate JSON",
                            "type": "invalid_request_error",
                            "code": "json_validate_failed",
                            "failed_generation": "",
                        }
                    },
                )

            return FakeResponse(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "executive_summary": "Summary.",
                                        "findings": [],
                                        "market_analysis": [],
                                        "competitor_landscape": [],
                                        "technical_feasibility": [],
                                        "customer_validation": [],
                                        "opportunities": [],
                                        "risks": [],
                                        "recommendations": [],
                                        "kpis": [],
                                        "roadmap": [],
                                    }
                                ),
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr(
        "src.core.llm.groq_client.httpx.AsyncClient",
        lambda timeout: FakeClient(),
    )

    result = await call_groq_structured(
        messages=[("system", "Return a report.")],
        schema=StrategyReport,
        model_name="test-model",
        api_key="test-key",
    )

    assert isinstance(result, StrategyReport)
    assert calls == ["json_schema", "json_object"]
