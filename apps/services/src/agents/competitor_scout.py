from __future__ import annotations

import hashlib
import logging
from typing import Any

from tavily import AsyncTavilyClient

from src.agents.base import BaseResearchAgent
from src.app.config import get_settings
from src.core.retry import ExternalAPIError, resilient_call
from src.core.schemas import AgentResult, ResearchTask, SourceDocument

MAX_RESULTS = 5
TAVILY_MAX_QUERY_CHARS = 380
TAVILY_QUERY_PREFIX = "competitors alternatives positioning startup"

logger = logging.getLogger(__name__)


class CompetitorScoutAgent(BaseResearchAgent):
    agent_name = "competitor"

    async def run(self, task: ResearchTask) -> AgentResult:
        logger.info("Running Competitor Scout")
        settings = get_settings()

        if settings.disable_live_calls:
            raise ValueError("Live research calls are disabled")
        if not settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is not configured")

        response = await search_competitors(
            query=task.query,
            api_key=settings.tavily_api_key,
        )
        documents = parse_competitor_documents(task, response)

        if not documents:
            raise ValueError("Tavily returned no competitor documents")

        return AgentResult(
            success=True,
            agent="competitor",
            output_summary=f"Found {len(documents)} competitor signals.",
            output_raw_docs=documents,
        )


@resilient_call(max_attempts=3)
async def search_competitors(
    query: str,
    api_key: str,
) -> dict[str, Any]:
    logger.info("Searching Tavily for competitors")
    client = AsyncTavilyClient(api_key=api_key)

    try:
        return await client.search(
            query=build_tavily_query(query),
            search_depth="advanced",
            topic="general",
            max_results=MAX_RESULTS,
            include_answer=True,
            include_raw_content=False,
            timeout=20,
        )
    except Exception as error:
        raise ExternalAPIError(str(error)) from error


def build_tavily_query(query: str) -> str:
    logger.debug("Building Tavily competitor query")
    value = clean_text(f"{TAVILY_QUERY_PREFIX} {query}")
    if len(value) <= TAVILY_MAX_QUERY_CHARS:
        return value

    trimmed = value[:TAVILY_MAX_QUERY_CHARS].rsplit(" ", 1)[0]
    return trimmed or value[:TAVILY_MAX_QUERY_CHARS]


def parse_competitor_documents(
    task: ResearchTask,
    response: dict[str, Any],
) -> list[SourceDocument]:
    logger.info("Parsing competitor documents")
    documents: list[SourceDocument] = []

    answer = clean_text(str(response.get("answer") or ""))
    if answer:
        documents.append(
            SourceDocument(
                doc_id=build_doc_id("competitor", task.task_id, "answer", answer),
                title=f"Tavily competitor overview for {task.query}",
                content=answer,
                agent="competitor",
            )
        )

    for index, result in enumerate(response.get("results", [])[:MAX_RESULTS], start=1):
        if not isinstance(result, dict):
            continue

        title = clean_text(str(result.get("title") or f"Competitor source {index}"))
        content = clean_text(str(result.get("content") or result.get("raw_content") or ""))
        url = clean_text(str(result.get("url") or ""))

        if not content:
            continue

        documents.append(
            SourceDocument(
                doc_id=build_doc_id("competitor", task.task_id, str(index), url or title),
                source_url=url or None,
                title=title,
                content=content,
                agent="competitor",
            )
        )

    return documents


def build_doc_id(*parts: str) -> str:
    logger.debug("Building competitor document id")
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{parts[0]}-{digest}"


def clean_text(value: str) -> str:
    logger.debug("Cleaning competitor text")
    return " ".join(value.split())
