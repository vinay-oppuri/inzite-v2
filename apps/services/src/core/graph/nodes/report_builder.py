from __future__ import annotations

import logging
from collections import Counter

from src.core.schemas import Finding, GraphState, SourceDocument

logger = logging.getLogger(__name__)


async def report_builder_node(state: GraphState) -> dict:
    """Render the validated StrategyReport into detailed Markdown."""
    if state.strategy is None:
        raise ValueError("strategy_engine_node must run first")

    logger.info("Running Report Builder")
    strategy = state.strategy
    lines = [
        f"# Startup Research Report: {state.idea_raw}",
        "",
        "## Executive Summary",
        strategy.executive_summary,
    ]

    append_startup_brief(lines, state)
    append_research_methodology(lines, state)
    append_findings(lines, "Key Findings", strategy.findings)
    append_findings(lines, "Market And Trend Analysis", strategy.market_analysis)
    append_findings(lines, "Competitor Landscape", strategy.competitor_landscape)
    append_findings(lines, "Technical Feasibility", strategy.technical_feasibility)
    append_findings(lines, "Customer Validation Plan", strategy.customer_validation)
    append_findings(lines, "Opportunities", strategy.opportunities)
    append_findings(lines, "Risks And Open Questions", strategy.risks)
    append_list(lines, "Recommendations", strategy.recommendations)
    append_list(lines, "KPIs To Track", strategy.kpis)
    append_list(lines, "Execution Roadmap", strategy.roadmap)
    append_evidence_matrix(lines, state.retrieved_docs)
    append_sources(lines, state.retrieved_docs)
    append_run_notes(lines, state.error_log)

    return {"final_report_markdown": "\n".join(lines)}


def append_startup_brief(lines: list[str], state: GraphState) -> None:
    logger.debug("Appending startup brief")
    lines.extend(["", "## Startup Brief"])
    if state.intent is None:
        lines.append(f"- Raw idea: {state.idea_raw}")
        return

    intent = state.intent
    lines.extend(
        [
            f"- Raw idea: {intent.idea_raw}",
            f"- Industry: {intent.industry}",
            f"- Target audience: {intent.target_audience}",
            f"- Business model: {intent.business_model.value}",
            f"- Problem statement: {intent.problem_statement}",
            f"- Proposed solution: {intent.proposed_solution}",
            f"- Data needs: {', '.join(intent.data_needs) if intent.data_needs else 'unspecified'}",
            f"- Agents triggered: {', '.join(intent.agent_triggers)}",
        ]
    )


def append_research_methodology(lines: list[str], state: GraphState) -> None:
    logger.debug("Appending research methodology")
    counts = Counter(doc.agent for doc in state.retrieved_docs)
    total = len(state.retrieved_docs)
    lines.extend(
        [
            "",
            "## Research Methodology And Coverage",
            (
                f"- Evidence base: {total} retrieved source documents "
                f"({counts.get('competitor', 0)} competitor, "
                f"{counts.get('paper', 0)} technical/research, "
                f"{counts.get('trend', 0)} trend)."
            ),
            "- Competitor research looks for alternatives, positioning, and substitute workflows.",
            "- Paper research looks for methods, benchmarks, and implementation evidence.",
            "- Trend research looks for news, market movement, and community adoption signals.",
            "- Every factual claim below is cited when supported by retrieved evidence.",
        ]
    )


def append_findings(lines: list[str], title: str, findings: list[Finding]) -> None:
    logger.debug("Appending report section %s", title)
    lines.extend(["", f"## {title}"])
    if not findings:
        lines.append("- No supported evidence found for this section.")
        return

    for index, finding in enumerate(findings, start=1):
        cite_ids = ", ".join(citation.doc_id for citation in finding.citations)
        source = f"Sources: {cite_ids}" if cite_ids else "UNVERIFIED"
        lines.append(f"{index}. {finding.statement}")
        lines.append(f"   - Evidence status: {source}")
        for citation in finding.citations:
            lines.append(f"   - `{citation.doc_id}`: {citation.quote_or_paraphrase}")


def append_list(lines: list[str], title: str, items: list[str]) -> None:
    logger.debug("Appending report list %s", title)
    lines.extend(["", f"## {title}"])
    if not items:
        lines.append("- No items generated.")
        return

    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item}")


def append_evidence_matrix(lines: list[str], documents: list[SourceDocument]) -> None:
    logger.debug("Appending evidence matrix")
    lines.extend(["", "## Evidence Matrix"])
    if not documents:
        lines.append("- No source documents were retrieved.")
        return

    lines.append("| Doc ID | Agent | Title | Evidence Preview |")
    lines.append("|---|---|---|---|")
    for doc in documents:
        lines.append(
            "| "
            f"`{doc.doc_id}` | "
            f"{doc.agent} | "
            f"{escape_table(doc.title)} | "
            f"{escape_table(truncate(doc.content, 180))} |"
        )


def append_sources(lines: list[str], documents: list[SourceDocument]) -> None:
    logger.debug("Appending sources")
    lines.extend(["", "## Sources"])
    if not documents:
        lines.append("- No source documents available.")
        return

    for doc in documents:
        source = f" - {doc.source_url}" if doc.source_url else ""
        published = f" ({doc.published_at.date()})" if doc.published_at else ""
        lines.append(f"- `{doc.doc_id}` [{doc.agent}] {doc.title}{published}{source}")


def append_run_notes(lines: list[str], errors: list[str]) -> None:
    logger.debug("Appending run notes")
    if not errors:
        return

    lines.extend(["", "## Run Notes"])
    for error in errors:
        lines.append(f"- {error}")


def truncate(value: str, max_chars: int) -> str:
    logger.debug("Truncating report text")
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def escape_table(value: str) -> str:
    logger.debug("Escaping Markdown table text")
    return value.replace("|", "\\|").replace("\n", " ")
