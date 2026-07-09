import pytest

from src.agents.competitor_scout import CompetitorScoutAgent
from src.agents.competitor_scout import build_tavily_query as build_competitor_query
from src.agents.paper_miner import PaperMinerAgent
from src.agents.paper_miner import RateLimitError
from src.agents.paper_miner import build_paper_query
from src.agents.trend_scraper import TrendScraperAgent
from src.agents.trend_scraper import build_tavily_query as build_trend_query
from src.app.config import get_settings
from src.core.schemas import ResearchTask


def task(agent: str) -> ResearchTask:
    return ResearchTask(
        task_id=f"{agent}-1",
        agent=agent,
        query="AI copilot for job seekers",
    )


def test_tavily_queries_stay_under_api_limit():
    long_query = " ".join(["freshers job search application"] * 60)

    competitor_query = build_competitor_query(long_query)
    trend_query = build_trend_query(long_query)

    assert len(competitor_query) <= 380
    assert len(trend_query) <= 380
    assert competitor_query.startswith("competitors alternatives")
    assert trend_query.startswith("market trends")


def test_paper_query_stays_compact():
    long_query = " ".join(["freshers job search application technical evidence"] * 30)

    paper_query = build_paper_query(long_query)

    assert len(paper_query) <= 300


@pytest.mark.asyncio
async def test_competitor_agent_requires_tavily_key(monkeypatch):
    monkeypatch.setenv("DISABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("TAVILY_API_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        await CompetitorScoutAgent().run(task("competitor"))


@pytest.mark.asyncio
async def test_competitor_agent_parses_mocked_tavily_response(monkeypatch):
    async def fake_search(query, api_key):
        return {
            "answer": "Several AI resume tools compete for job seeker workflows.",
            "results": [
                {
                    "title": "Resume AI",
                    "url": "https://example.com/resume-ai",
                    "content": "Resume AI helps job seekers tailor applications.",
                }
            ],
        }

    monkeypatch.setenv("DISABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("src.agents.competitor_scout.search_competitors", fake_search)

    result = await CompetitorScoutAgent().run(task("competitor"))

    assert result.success is True
    assert result.agent == "competitor"
    assert len(result.output_raw_docs) == 2
    assert result.output_raw_docs[1].source_url is not None


@pytest.mark.asyncio
async def test_paper_agent_parses_mocked_semantic_scholar_response(monkeypatch):
    async def fake_search(query, api_key):
        return {
            "data": [
                {
                    "title": "Resume Tailoring With Language Models",
                    "abstract": "Large language models can adapt resumes to job descriptions.",
                    "url": "https://example.com/paper",
                    "year": 2025,
                    "authors": [{"name": "Ada Lovelace"}],
                    "venue": "ExampleConf",
                    "citationCount": 7,
                }
            ]
        }

    monkeypatch.setenv("DISABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("src.agents.paper_miner.search_papers", fake_search)

    result = await PaperMinerAgent().run(task("paper"))

    assert result.success is True
    assert result.output_raw_docs[0].agent == "paper"
    assert result.output_raw_docs[0].source_url is not None
    assert "Ada Lovelace" in result.output_raw_docs[0].content


@pytest.mark.asyncio
async def test_paper_agent_tolerates_semantic_scholar_rate_limit(monkeypatch):
    async def fake_search(query, api_key):
        raise RateLimitError("Semantic Scholar rate limit reached")

    monkeypatch.setenv("DISABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("src.agents.paper_miner.search_papers", fake_search)

    result = await PaperMinerAgent().run(task("paper"))

    assert result.success is True
    assert result.output_raw_docs == []
    assert "rate-limited" in result.output_summary


@pytest.mark.asyncio
async def test_trend_agent_tolerates_partial_source_failure(monkeypatch):
    async def fake_news(query, api_key):
        return {
            "articles": [
                {
                    "title": "AI job search tools gain adoption",
                    "description": "Career platforms are adding AI support.",
                    "content": "Job seekers use AI tools to tailor applications.",
                    "url": "https://example.com/news",
                    "publishedAt": "2026-01-01T00:00:00Z",
                    "source": {"name": "Example News"},
                }
            ]
        }

    async def fake_reddit(query):
        raise RuntimeError("reddit unavailable")

    monkeypatch.setenv("DISABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("NEWS_API_KEY", "test-news-key")
    monkeypatch.setenv("ENABLE_KEYLESS_LIVE_SOURCES", "true")
    get_settings.cache_clear()
    monkeypatch.setattr("src.agents.trend_scraper.search_news", fake_news)
    monkeypatch.setattr("src.agents.trend_scraper.search_reddit", fake_reddit)

    result = await TrendScraperAgent().run(task("trend"))

    assert result.success is True
    assert result.output_raw_docs[0].agent == "trend"
    assert "Partial source failures" in result.output_summary
