from src.core.schemas import (
    AgentResult,
    BusinessModel,
    Citation,
    Finding,
    GraphState,
    SourceDocument,
    StartupIntent,
)


def test_startup_intent_defaults_agent_triggers():
    intent = StartupIntent(
        idea_raw="AI copilot for job seekers",
        industry="HR tech",
        target_audience="job seekers",
        business_model=BusinessModel.b2c,
        problem_statement="job search is slow",
        proposed_solution="AI copilot",
    )
    assert intent.agent_triggers == ["competitor", "paper", "trend"]


def test_finding_without_citation_is_still_valid_but_flaggable():
    finding = Finding(statement="Unverified claim")
    assert finding.citations == []


def test_agent_result_failure_shape():
    result = AgentResult(
        success=False,
        agent="trend",
        output_summary="",
        output_raw_docs=[],
        error="timeout",
    )
    assert result.success is False
    assert result.error == "timeout"


def test_graph_state_round_trip():
    doc = SourceDocument(
        doc_id="d1",
        title="Example",
        content="Example content",
        agent="competitor",
    )
    state = GraphState(run_id="r1", idea_raw="idea", retrieved_docs=[doc])
    dumped = state.model_dump()
    rebuilt = GraphState(**dumped)
    assert rebuilt.retrieved_docs[0].doc_id == "d1"
