import pytest

from src.app.config import get_settings
from src.core.graph.nodes.intent_parser import intent_parser_node
from src.core.schemas import BusinessModel, GraphState, StartupIntent


@pytest.mark.asyncio
async def test_intent_parser_uses_groq_structured_output(monkeypatch):
    async def fake_generate_structured(messages, schema):
        assert schema is StartupIntent
        assert "AI copilot for job seekers" in messages[1][1]
        return StartupIntent(
            idea_raw="AI copilot for job seekers",
            industry="HR tech",
            target_audience="job seekers",
            business_model=BusinessModel.b2c,
            problem_statement="Job seekers spend too much time tailoring resumes.",
            proposed_solution="AI copilot for job seekers",
            data_needs=["technical feasibility evidence"],
            agent_triggers=["competitor", "paper", "trend"],
        )

    monkeypatch.setenv("DISABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "src.core.graph.nodes.intent_parser.generate_structured",
        fake_generate_structured,
    )

    result = await intent_parser_node(
        GraphState(run_id="intent-test", idea_raw="AI copilot for job seekers")
    )

    assert result["intent"].industry == "HR tech"
    assert result["intent"].target_audience == "job seekers"
    assert result["intent"].business_model == BusinessModel.b2c


@pytest.mark.asyncio
async def test_intent_parser_raises_when_groq_key_is_missing(monkeypatch):
    monkeypatch.setenv("DISABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    state = GraphState(run_id="intent-test", idea_raw="AI copilot for job seekers")

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        await intent_parser_node(state)
