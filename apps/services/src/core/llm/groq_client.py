from __future__ import annotations

import json
import re
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src.app.config import get_settings
from src.core.retry import ExternalAPIError, resilient_call

SchemaT = TypeVar("SchemaT", bound=BaseModel)

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
RETRYABLE_STATUS_CODES = {408, 409, 429}


class GroqRequestError(Exception):
    """Non-retryable error response from Groq."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Groq request failed with HTTP {status_code}: {body[:500]}")


async def generate_structured(
    messages: list[tuple[str, str]],
    schema: type[SchemaT],
) -> SchemaT:
    """Call Groq and return validated structured output."""

    settings = get_settings()
    if settings.disable_live_calls:
        raise ValueError("Live LLM calls are disabled")
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not configured")

    return await call_groq_structured(
        messages=messages,
        schema=schema,
        model_name=settings.groq_model,
        api_key=settings.groq_api_key,
    )


async def call_groq_structured(
    messages: list[tuple[str, str]],
    schema: type[SchemaT],
    model_name: str,
    api_key: str,
) -> SchemaT:
    """Call Groq JSON Schema mode, then fall back to JSON Object mode if needed."""

    try:
        response = await post_groq(
            build_json_schema_payload(messages, schema, model_name),
            api_key,
        )
    except GroqRequestError as error:
        if not is_json_schema_generation_error(error):
            raise

        response = await post_groq(
            build_json_object_payload(messages, schema, model_name),
            api_key,
        )

    return parse_structured_response(response, schema)


@resilient_call(max_attempts=2, min_wait=0.5, max_wait=2.0)
async def post_groq(
    payload: dict,
    api_key: str,
) -> dict:
    """Post to Groq and retry only transient transport/provider failures."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_CHAT_COMPLETIONS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as error:
        raise ExternalAPIError(str(error)) from error

    if is_retryable_response(response):
        raise ExternalAPIError(
            f"Groq request failed with HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    if response.is_error:
        raise GroqRequestError(response.status_code, response.text)

    try:
        return response.json()
    except ValueError as error:
        raise ExternalAPIError(str(error)) from error


def parse_structured_response(
    response: dict,
    schema: type[SchemaT],
) -> SchemaT:
    content = response["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Groq response did not include message content")

    return schema.model_validate(json.loads(content))


def build_json_schema_payload(
    messages: list[tuple[str, str]],
    schema: type[BaseModel],
    model_name: str,
) -> dict:
    return {
        "model": model_name,
        "messages": format_messages(messages),
        "temperature": 0.1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name(schema),
                "strict": False,
                "schema": schema.model_json_schema(),
            },
        },
    }


def build_json_object_payload(
    messages: list[tuple[str, str]],
    schema: type[BaseModel],
    model_name: str,
) -> dict:
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=True)
    json_instruction = (
        "Return one valid JSON object only. Do not include markdown. "
        "The JSON object must validate against this schema: "
        f"{schema_json}"
    )

    return {
        "model": model_name,
        "messages": format_messages([("system", json_instruction), *messages]),
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }


def format_messages(messages: list[tuple[str, str]]) -> list[dict[str, str]]:
    role_map = {
        "human": "user",
        "ai": "assistant",
    }
    return [
        {
            "role": role_map.get(role, role),
            "content": content,
        }
        for role, content in messages
    ]


def schema_name(schema: type[BaseModel]) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", schema.__name__).strip("_").lower()


def is_retryable_response(response: httpx.Response) -> bool:
    return response.status_code in RETRYABLE_STATUS_CODES or response.status_code >= 500


def is_json_schema_generation_error(error: GroqRequestError) -> bool:
    if error.status_code != 400:
        return False

    try:
        payload = json.loads(error.body)
    except ValueError:
        return False

    details = payload.get("error", {})
    return details.get("code") == "json_validate_failed"
