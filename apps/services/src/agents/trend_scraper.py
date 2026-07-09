from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from tavily import AsyncTavilyClient

from src.agents.base import BaseResearchAgent
from src.app.config import get_settings
from src.core.retry import ExternalAPIError, resilient_call
from src.core.schemas import AgentResult, ResearchTask, SourceDocument

NEWS_API_URL = "https://newsapi.org/v2/everything"
REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
MAX_RESULTS = 5
TAVILY_MAX_QUERY_CHARS = 380
TAVILY_QUERY_PREFIX = "market trends adoption community discussion startup"
USER_AGENT = "inzite-startup-research-agent/0.1"

logger = logging.getLogger(__name__)


class TrendScraperAgent(BaseResearchAgent):
    agent_name = "trend"

    async def run(self, task: ResearchTask) -> AgentResult:
        logger.info("Running Trend Scraper")
        settings = get_settings()

        if settings.disable_live_calls:
            raise ValueError("Live research calls are disabled")

        documents: list[SourceDocument] = []
        errors: list[str] = []
        source_count = 0

        if settings.news_api_key:
            source_count += 1
            try:
                response = await search_news(task.query, settings.news_api_key)
                documents.extend(parse_news_documents(task, response))
            except Exception as error:
                errors.append(f"NewsAPI failed: {error}")

        if settings.enable_keyless_live_sources:
            source_count += 1
            try:
                response = await search_reddit(task.query)
                documents.extend(parse_reddit_documents(task, response))
            except Exception as error:
                errors.append(f"Reddit failed: {error}")

        if settings.tavily_api_key:
            source_count += 1
            try:
                response = await search_tavily_trends(task.query, settings.tavily_api_key)
                documents.extend(parse_tavily_documents(task, response))
            except Exception as error:
                errors.append(f"Tavily failed: {error}")

        if not source_count:
            raise ValueError("No trend source is configured")
        if not documents:
            raise ValueError("; ".join(errors) or "Trend sources returned no documents")

        summary = f"Found {len(documents)} trend signals."
        if errors:
            summary = f"{summary} Partial source failures: {'; '.join(errors)}"

        return AgentResult(
            success=True,
            agent="trend",
            output_summary=summary,
            output_raw_docs=documents,
        )


@resilient_call(max_attempts=3)
async def search_news(
    query: str,
    api_key: str,
) -> dict[str, Any]:
    logger.info("Searching NewsAPI for trends")
    params = {
        "q": query,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": MAX_RESULTS,
        "apiKey": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(NEWS_API_URL, params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ExternalAPIError(str(error)) from error


@resilient_call(max_attempts=3)
async def search_reddit(query: str) -> dict[str, Any]:
    logger.info("Searching Reddit for trends")
    params = {
        "q": query,
        "sort": "relevance",
        "t": "year",
        "limit": MAX_RESULTS,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(REDDIT_SEARCH_URL, params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ExternalAPIError(str(error)) from error


@resilient_call(max_attempts=3)
async def search_tavily_trends(
    query: str,
    api_key: str,
) -> dict[str, Any]:
    logger.info("Searching Tavily for trends")
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
    logger.debug("Building Tavily trend query")
    value = clean_text(f"{TAVILY_QUERY_PREFIX} {query}")
    if len(value) <= TAVILY_MAX_QUERY_CHARS:
        return value

    trimmed = value[:TAVILY_MAX_QUERY_CHARS].rsplit(" ", 1)[0]
    return trimmed or value[:TAVILY_MAX_QUERY_CHARS]


def parse_news_documents(
    task: ResearchTask,
    response: dict[str, Any],
) -> list[SourceDocument]:
    logger.info("Parsing NewsAPI trend documents")
    documents: list[SourceDocument] = []

    for index, article in enumerate(response.get("articles", [])[:MAX_RESULTS], start=1):
        if not isinstance(article, dict):
            continue

        title = clean_text(str(article.get("title") or f"News source {index}"))
        description = clean_text(str(article.get("description") or ""))
        content = clean_text(str(article.get("content") or ""))
        body = ". ".join(part for part in (description, content) if part)
        url = clean_text(str(article.get("url") or ""))

        if not body:
            continue

        source = article.get("source") if isinstance(article.get("source"), dict) else {}
        source_name = clean_text(str(source.get("name") or "NewsAPI"))

        documents.append(
            SourceDocument(
                doc_id=build_doc_id("trend-news", task.task_id, str(index), url or title),
                source_url=url or None,
                title=f"{title} ({source_name})",
                content=body,
                published_at=parse_datetime(article.get("publishedAt")),
                agent="trend",
            )
        )

    return documents


def parse_reddit_documents(
    task: ResearchTask,
    response: dict[str, Any],
) -> list[SourceDocument]:
    logger.info("Parsing Reddit trend documents")
    documents: list[SourceDocument] = []
    children = response.get("data", {}).get("children", [])

    for index, child in enumerate(children[:MAX_RESULTS], start=1):
        data = child.get("data", {}) if isinstance(child, dict) else {}
        if not isinstance(data, dict):
            continue

        title = clean_text(str(data.get("title") or f"Reddit source {index}"))
        selftext = clean_text(str(data.get("selftext") or ""))
        subreddit = clean_text(str(data.get("subreddit_name_prefixed") or "reddit"))
        permalink = clean_text(str(data.get("permalink") or ""))
        url = f"https://www.reddit.com{permalink}" if permalink else ""

        content = build_reddit_content(
            text=selftext or title,
            score=data.get("score"),
            comments=data.get("num_comments"),
        )

        documents.append(
            SourceDocument(
                doc_id=build_doc_id("trend-reddit", task.task_id, str(index), url or title),
                source_url=url or None,
                title=f"{title} ({subreddit})",
                content=content,
                published_at=parse_reddit_datetime(data.get("created_utc")),
                agent="trend",
            )
        )

    return documents


def parse_tavily_documents(
    task: ResearchTask,
    response: dict[str, Any],
) -> list[SourceDocument]:
    logger.info("Parsing Tavily trend documents")
    documents: list[SourceDocument] = []

    answer = clean_text(str(response.get("answer") or ""))
    if answer:
        documents.append(
            SourceDocument(
                doc_id=build_doc_id("trend-tavily", task.task_id, "answer", answer),
                title=f"Tavily trend overview for {task.query}",
                content=answer,
                agent="trend",
            )
        )

    for index, result in enumerate(response.get("results", [])[:MAX_RESULTS], start=1):
        if not isinstance(result, dict):
            continue

        title = clean_text(str(result.get("title") or f"Tavily source {index}"))
        content = clean_text(str(result.get("content") or result.get("raw_content") or ""))
        url = clean_text(str(result.get("url") or ""))

        if not content:
            continue

        documents.append(
            SourceDocument(
                doc_id=build_doc_id("trend-tavily", task.task_id, str(index), url or title),
                source_url=url or None,
                title=title,
                content=content,
                agent="trend",
            )
        )

    return documents


def build_reddit_content(
    text: str,
    score: Any,
    comments: Any,
) -> str:
    logger.debug("Building Reddit trend content")
    parts = [text]
    if score is not None:
        parts.append(f"Score: {score}")
    if comments is not None:
        parts.append(f"Comments: {comments}")
    return ". ".join(parts)


def parse_datetime(value: Any) -> datetime | None:
    logger.debug("Parsing trend datetime")
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_reddit_datetime(value: Any) -> datetime | None:
    logger.debug("Parsing Reddit trend datetime")
    if not isinstance(value, (int, float)):
        return None

    return datetime.fromtimestamp(value, tz=timezone.utc)


def build_doc_id(*parts: str) -> str:
    logger.debug("Building trend document id")
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{parts[0]}-{digest}"


def clean_text(value: str) -> str:
    logger.debug("Cleaning trend text")
    return " ".join(value.split())
