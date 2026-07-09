import pytest

from src.app.config import get_settings
from src.core.schemas import AgentResult, BusinessModel, SourceDocument, StartupIntent


@pytest.fixture(autouse=True)
def disable_live_llm_calls(monkeypatch):
    monkeypatch.setenv("DISABLE_LIVE_CALLS", "true")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("NEWS_API_KEY", "")
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "")
    monkeypatch.setenv("ENABLE_KEYLESS_LIVE_SOURCES", "false")
    monkeypatch.setenv("ENABLE_RAG_INDEXING", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_groq_intent(monkeypatch):
    async def fake_generate_structured(messages, schema):
        return StartupIntent(
            idea_raw="AI copilot for job seekers",
            industry="HR tech",
            target_audience="job seekers",
            business_model=BusinessModel.b2c,
            problem_statement="Job seekers spend too much time tailoring resumes.",
            proposed_solution="AI copilot for job seekers",
            data_needs=["competitor landscape", "technical feasibility evidence"],
            agent_triggers=["competitor", "paper", "trend"],
        )

    get_settings.cache_clear()
    monkeypatch.setattr(
        "src.core.graph.nodes.intent_parser.generate_structured",
        fake_generate_structured,
    )
    return fake_generate_structured


@pytest.fixture
def mock_agent_registry(monkeypatch):
    class FakeAgent:
        def __init__(self, agent: str):
            self.agent = agent

        async def run(self, task):
            document = SourceDocument(
                doc_id=f"{self.agent}-mock-{task.task_id}",
                title=f"Mock {self.agent} source",
                content=f"Mock {self.agent} evidence for {task.query}.",
                agent=self.agent,
            )
            return AgentResult(
                success=True,
                agent=self.agent,
                output_summary=f"Mock {self.agent} completed.",
                output_raw_docs=[document],
            )

    registry = {
        "competitor": FakeAgent("competitor"),
        "paper": FakeAgent("paper"),
        "trend": FakeAgent("trend"),
    }
    monkeypatch.setattr(
        "src.core.graph.nodes.research_fanout.AGENT_REGISTRY",
        registry,
    )
    return registry
