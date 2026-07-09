from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from src.agents.base import BaseResearchAgent
from src.app.config import get_settings
from src.core.retry import ExternalAPIError, resilient_call
from src.core.schemas import AgentResult, ResearchTask, SourceDocument

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_RESULTS = 5
MAX_QUERY_CHARS = 300
USER_AGENT = "inzite-startup-research-agent/0.1"

logger = logging.getLogger(__name__)


class RateLimitError(ExternalAPIError):
    """Semantic Scholar rate limit was reached."""


class PaperMinerAgent(BaseResearchAgent):
    agent_name = "paper"

    async def run(self, task: ResearchTask) -> AgentResult:
        logger.info("Running Paper Miner")
        settings = get_settings()

        if settings.disable_live_calls:
            raise ValueError("Live research calls are disabled")
        if not settings.semantic_scholar_api_key and not settings.enable_keyless_live_sources:
            raise ValueError(
                "Semantic Scholar is not configured. Set SEMANTIC_SCHOLAR_API_KEY "
                "or ENABLE_KEYLESS_LIVE_SOURCES=true."
            )

        try:
            response = await search_papers(
                query=task.query,
                api_key=settings.semantic_scholar_api_key or None,
            )
        except RateLimitError:
            return AgentResult(
                success=True,
                agent="paper",
                output_summary="Semantic Scholar rate-limited paper search; continuing without paper documents.",
                output_raw_docs=[],
            )

        documents = parse_paper_documents(task, response)

        if not documents:
            return AgentResult(
                success=True,
                agent="paper",
                output_summary="Semantic Scholar returned no paper documents.",
                output_raw_docs=[],
            )

        return AgentResult(
            success=True,
            agent="paper",
            output_summary=f"Found {len(documents)} technical research signals.",
            output_raw_docs=documents,
        )


@resilient_call(max_attempts=3)
async def search_papers(
    query: str,
    api_key: str | None,
) -> dict[str, Any]:
    logger.info("Searching Semantic Scholar for papers")
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["x-api-key"] = api_key

    params = {
        "query": build_paper_query(query),
        "limit": MAX_RESULTS,
        "fields": "title,abstract,url,year,authors,venue,publicationDate,citationCount",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
            response = await client.get(SEMANTIC_SCHOLAR_URL, params=params)
            if response.status_code == 429:
                raise RateLimitError("Semantic Scholar rate limit reached")
            response.raise_for_status()
            return response.json()
    except RateLimitError:
        raise
    except (httpx.HTTPError, ValueError) as error:
        raise ExternalAPIError(str(error)) from error


def build_paper_query(query: str) -> str:
    logger.debug("Building Semantic Scholar paper query")
    value = clean_text(query)
    if len(value) <= MAX_QUERY_CHARS:
        return value

    trimmed = value[:MAX_QUERY_CHARS].rsplit(" ", 1)[0]
    return trimmed or value[:MAX_QUERY_CHARS]


def parse_paper_documents(
    task: ResearchTask,
    response: dict[str, Any],
) -> list[SourceDocument]:
    logger.info("Parsing paper documents")
    documents: list[SourceDocument] = []

    for index, paper in enumerate(response.get("data", [])[:MAX_RESULTS], start=1):
        if not isinstance(paper, dict):
            continue

        title = clean_text(str(paper.get("title") or f"Research paper {index}"))
        abstract = clean_text(str(paper.get("abstract") or ""))
        url = clean_text(str(paper.get("url") or ""))

        if not abstract:
            continue

        documents.append(
            SourceDocument(
                doc_id=build_doc_id("paper", task.task_id, str(index), url or title),
                source_url=url or None,
                title=title,
                content=build_paper_content(paper, abstract),
                published_at=parse_publication_date(paper),
                agent="paper",
            )
        )

    return documents


def build_paper_content(
    paper: dict[str, Any],
    abstract: str,
) -> str:
    logger.debug("Building paper document content")
    metadata = [
        f"Authors: {authors}" if (authors := parse_authors(paper)) else "",
        f"Year: {year}" if (year := paper.get("year")) else "",
        f"Venue: {venue}" if (venue := clean_text(str(paper.get("venue") or ""))) else "",
        f"Citations: {count}" if (count := paper.get("citationCount")) is not None else "",
    ]
    metadata_text = "; ".join(part for part in metadata if part)

    if not metadata_text:
        return abstract

    return f"{metadata_text}. Abstract: {abstract}"


def parse_authors(paper: dict[str, Any]) -> str:
    logger.debug("Parsing paper authors")
    authors = paper.get("authors", [])
    if not isinstance(authors, list):
        return ""

    return ", ".join(
        clean_text(str(author.get("name", "")))
        for author in authors
        if isinstance(author, dict) and author.get("name")
    )


def parse_publication_date(paper: dict[str, Any]) -> datetime | None:
    logger.debug("Parsing paper publication date")
    raw_date = paper.get("publicationDate")
    if isinstance(raw_date, str) and raw_date:
        try:
            return datetime.fromisoformat(raw_date).replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    year = paper.get("year")
    if isinstance(year, int):
        return datetime(year, 1, 1, tzinfo=timezone.utc)

    return None


def build_doc_id(*parts: str) -> str:
    logger.debug("Building paper document id")
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{parts[0]}-{digest}"


def clean_text(value: str) -> str:
    logger.debug("Cleaning paper text")
    return " ".join(value.split())
