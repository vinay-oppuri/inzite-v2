import pytest

from src.core.graph.nodes.report_builder import report_builder_node
from src.core.graph.nodes.strategy_engine import strategy_engine_node
from src.core.schemas import GraphState, SourceDocument, StartupIntent


@pytest.mark.asyncio
async def test_strategy_report_cites_retrieved_documents():
    intent = StartupIntent(
        idea_raw="AI copilot for job seekers",
        industry="HR tech",
        target_audience="job seekers",
        business_model="b2c",
        problem_statement="Job seekers need faster resume tailoring.",
        proposed_solution="AI copilot for job seekers",
    )
    doc = SourceDocument(
        doc_id="competitor-1",
        title="Competitor signal",
        content="Competitors offer resume tailoring for job seekers.",
        agent="competitor",
    )
    state = GraphState(
        run_id="strategy-test",
        idea_raw=intent.idea_raw,
        intent=intent,
        retrieved_docs=[doc],
    )

    result = await strategy_engine_node(state)

    assert result["strategy"].findings
    assert result["strategy"].findings[0].citations[0].doc_id == "competitor-1"


@pytest.mark.asyncio
async def test_report_builder_renders_sources_and_sections():
    intent = StartupIntent(
        idea_raw="AI copilot for job seekers",
        industry="HR tech",
        target_audience="job seekers",
        business_model="b2c",
        problem_statement="Job seekers need faster resume tailoring.",
        proposed_solution="AI copilot for job seekers",
    )
    doc = SourceDocument(
        doc_id="competitor-1",
        title="Competitor signal",
        content="Competitors offer resume tailoring for job seekers.",
        agent="competitor",
    )
    state = GraphState(
        run_id="strategy-test",
        idea_raw=intent.idea_raw,
        intent=intent,
        retrieved_docs=[doc],
    )
    strategy_result = await strategy_engine_node(state)
    state.strategy = strategy_result["strategy"]

    report_result = await report_builder_node(state)
    report = report_result["final_report_markdown"]

    assert "## Executive Summary" in report
    assert "## Startup Brief" in report
    assert "## Research Methodology And Coverage" in report
    assert "## Market And Trend Analysis" in report
    assert "## Competitor Landscape" in report
    assert "## Technical Feasibility" in report
    assert "## Opportunities" in report
    assert "## Evidence Matrix" in report
    assert "## Sources" in report
    assert "`competitor-1`" in report
