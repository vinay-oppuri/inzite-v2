from __future__ import annotations

import logging
import re
import uuid
from typing import Any

import httpx

from src.core.retry import ExternalAPIError, resilient_call
from src.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


@resilient_call(max_attempts=3)
async def ensure_collection(
    qdrant_url: str,
    collection_name: str,
    vector_size: int,
    api_key: str = "",
) -> None:
    logger.info("Ensuring Qdrant collection %s", collection_name)
    payload = {"vectors": {"size": vector_size, "distance": "Cosine"}}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(
                f"{qdrant_url.rstrip('/')}/collections/{collection_name}",
                headers=qdrant_headers(api_key),
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise ExternalAPIError(str(error)) from error


@resilient_call(max_attempts=3)
async def upsert_documents(
    qdrant_url: str,
    collection_name: str,
    run_id: str,
    documents: list[SourceDocument],
    vectors: list[list[float]],
    api_key: str = "",
) -> None:
    logger.info("Upserting %s Qdrant documents", len(documents))
    points = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{document.doc_id}")),
            "vector": vector,
            "payload": build_payload(run_id, document),
        }
        for document, vector in zip(documents, vectors, strict=True)
    ]

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(
                f"{qdrant_url.rstrip('/')}/collections/{collection_name}/points",
                headers=qdrant_headers(api_key),
                params={"wait": "true"},
                json={"points": points},
            )
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise ExternalAPIError(str(error)) from error


def build_payload(
    run_id: str,
    document: SourceDocument,
) -> dict[str, Any]:
    logger.debug("Building Qdrant payload for %s", document.doc_id)
    return {
        "run_id": run_id,
        "doc_id": document.doc_id,
        "title": document.title,
        "content": document.content,
        "source_url": str(document.source_url) if document.source_url else None,
        "published_at": document.published_at.isoformat() if document.published_at else None,
        "agent": document.agent,
    }


def collection_name_for_run(run_id: str) -> str:
    logger.debug("Building Qdrant collection name for run %s", run_id)
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", run_id).strip("_").lower()
    return f"research_{value or 'run'}"


def qdrant_headers(api_key: str) -> dict[str, str]:
    logger.debug("Building Qdrant request headers")
    if not api_key:
        return {}
    return {"api-key": api_key}
