import pytest

from src.core.graph.builder import build_graph
from src.core.schemas import GraphState


@pytest.mark.asyncio
async def test_graph_runs_end_to_end_with_mocked_intent(
    mock_groq_intent,
    mock_agent_registry,
):
    graph = build_graph()
    initial_state = GraphState(run_id="smoke-test", idea_raw="AI copilot for job seekers")

    result = await graph.ainvoke(initial_state)

    assert result["intent"] is not None
    assert result["plan"] is not None
    assert len(result["agent_results"]) == 3  # competitor, paper, trend
    assert all(r.success for r in result["agent_results"])
    assert result["strategy"] is not None
    assert "AI copilot for job seekers" in result["final_report_markdown"]
    assert result["error_log"] == []
