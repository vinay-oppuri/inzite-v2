from __future__ import annotations

import json
import logging

from src.app.config import get_settings
from src.core.llm.groq_client import generate_structured
from src.core.rag.reranker import rerank_documents
from src.core.rag.retriever import retrieve_relevant_docs
from src.core.schemas import Citation, Finding, GraphState, SourceDocument, StrategyReport

MAX_CONTEXT_DOCS = 12
MAX_DOC_CHARS = 1200

logger = logging.getLogger(__name__)


async def strategy_engine_node(state: GraphState) -> dict:
    """Synthesize a cited strategy report from retrieved evidence."""
    if state.intent is None:
        raise ValueError("intent_parser_node must run first")

    logger.info("Running Strategy Engine")
    query = _strategy_query(state)
    retrieved = retrieve_relevant_docs(state.intent, state.retrieved_docs, limit=MAX_CONTEXT_DOCS)
    context_docs = rerank_documents(query, retrieved)
    logger.info("Strategy Engine selected %s context documents", len(context_docs))

    settings = get_settings()
    if settings.groq_api_key and not settings.disable_live_calls and context_docs:
        try:
            report = await synthesize_with_groq(state, context_docs)
            report = complete_report(report, state, context_docs)
            return {"strategy": _enforce_citations(report, state.retrieved_docs)}
        except Exception as exc:  # noqa: BLE001 - deterministic evidence report keeps the run usable
            logger.exception("Strategy Engine Groq synthesis failed")
            report = _build_evidence_report(state, context_docs)
            note = f"strategy_engine Groq synthesis failed: {exc}"
            return {"strategy": report, "error_log": [*state.error_log, note]}

    logger.info("Building local evidence strategy report")
    return {"strategy": _build_evidence_report(state, context_docs)}


async def synthesize_with_groq(
    state: GraphState,
    docs: list[SourceDocument],
) -> StrategyReport:
    if state.intent is None:
        raise ValueError("intent_parser_node must run first")

    logger.info("Synthesizing Strategy Report with Groq")
    source_context = json.dumps(_source_context(docs), ensure_ascii=True)
    return await generate_structured(
        [
            (
                "system",
                "You are a startup research strategist. Return only the StrategyReport schema. "
                "Always include every top-level field exactly once: executive_summary, findings, "
                "market_analysis, competitor_landscape, technical_feasibility, customer_validation, "
                "opportunities, risks, recommendations, kpis, and roadmap. Use an empty array when "
                "a list section has no supported content. All research sections must be detailed, "
                "consultant-style, and specific to the startup idea. findings, market_analysis, "
                "competitor_landscape, technical_feasibility, customer_validation, opportunities, "
                "and risks must each be an array of objects with statement and citations fields. "
                "citations must be an array of objects with doc_id and quote_or_paraphrase fields. "
                "Every factual finding, market point, competitor point, opportunity, and risk must "
                "cite one or more doc_id values from the provided source documents. Do not invent "
                "doc_id values. If evidence is weak, write a cautious statement and leave citations "
                "empty so it can be tagged unverified. Recommendations, KPIs, and roadmap items "
                "should be detailed, action-oriented, and avoid unsupported factual claims. "
                "When evidence supports it, include 2-4 substantive points per research section. "
                "Return JSON only.",
            ),
            (
                "human",
                "Startup intent:\n"
                f"{state.intent.model_dump_json()}\n\n"
                "Source documents:\n"
                f"{source_context}",
            ),
        ],
        schema=StrategyReport,
    )


def _build_evidence_report(
    state: GraphState,
    docs: list[SourceDocument],
) -> StrategyReport:
    logger.info("Building deterministic evidence report")
    if not docs:
        return StrategyReport(
            executive_summary=(
                "No external evidence was retrieved, so this report is a readiness note rather "
                "than a decision-grade research report."
            ),
            findings=[
                Finding(
                    statement="UNVERIFIED: No retrieved evidence was available for synthesis.",
                    citations=[],
                )
            ],
            market_analysis=[],
            competitor_landscape=[],
            technical_feasibility=[],
            customer_validation=[],
            opportunities=[],
            risks=[
                Finding(
                    statement="UNVERIFIED: The report needs live research evidence before decisions are made.",
                    citations=[],
                )
            ],
            recommendations=[
                "Configure at least one research source and rerun before using this as a decision document."
            ],
            kpis=["Number of retrieved source documents", "Share of findings with citations"],
            roadmap=["Connect live research sources", "Rerun the graph", "Review cited findings"],
        )

    intent = state.intent
    findings = [_finding_from_doc(doc) for doc in docs[:6]]
    market_analysis = [
        _finding_from_doc(doc, prefix="Market signal")
        for doc in docs
        if doc.agent == "trend"
    ][:4]
    competitor_landscape = [
        _finding_from_doc(doc, prefix="Competitive landscape signal")
        for doc in docs
        if doc.agent == "competitor"
    ][:4]
    technical_feasibility = [
        _finding_from_doc(doc, prefix="Technical feasibility signal")
        for doc in docs
        if doc.agent == "paper"
    ][:4]
    customer_validation = [
        Finding(
            statement=(
                f"UNVERIFIED: Validate whether {intent.target_audience if intent else 'the target audience'} "
                f"has the problem described as: {intent.problem_statement if intent else state.idea_raw}."
            ),
            citations=[],
        )
    ]
    opportunities = [
        _finding_from_doc(doc, prefix="Opportunity signal")
        for doc in docs
        if doc.agent in {"competitor", "trend"}
    ][:3]
    risks = [
        _finding_from_doc(doc, prefix="Risk or uncertainty signal")
        for doc in docs
        if _looks_like_uncertainty(doc)
    ][:3]

    if not risks and state.error_log:
        risks.append(
            Finding(
                statement=f"UNVERIFIED: Some research steps reported issues: {'; '.join(state.error_log[:2])}",
                citations=[],
            )
        )

    return StrategyReport(
        executive_summary=build_executive_summary(state, docs),
        findings=findings,
        market_analysis=market_analysis,
        competitor_landscape=competitor_landscape,
        technical_feasibility=technical_feasibility,
        customer_validation=customer_validation,
        opportunities=opportunities,
        risks=risks,
        recommendations=[
            "Validate the top cited customer problem with 5-10 target users.",
            "Compare positioning against the cited competitor and substitute signals.",
            "Prototype the smallest workflow that proves the cited technical or trend assumptions.",
        ],
        kpis=[
            "Cited evidence coverage by agent",
            "Qualified user interviews completed",
            "Prototype task completion rate",
            "Waitlist or pilot conversion rate",
        ],
        roadmap=[
            "Week 1: review cited evidence and define riskiest assumption",
            "Weeks 2-3: interview target users and map competitor positioning",
            "Weeks 4-6: build a focused prototype around the strongest cited pain point",
            "Weeks 7-8: run pilot tests and update the strategy with fresh citations",
        ],
    )


def _enforce_citations(
    report: StrategyReport,
    source_docs: list[SourceDocument],
) -> StrategyReport:
    logger.debug("Enforcing Strategy Report citations")
    valid_doc_ids = {doc.doc_id for doc in source_docs}
    return StrategyReport(
        executive_summary=report.executive_summary,
        findings=_normalize_findings(report.findings, valid_doc_ids),
        market_analysis=_normalize_findings(report.market_analysis, valid_doc_ids),
        competitor_landscape=_normalize_findings(report.competitor_landscape, valid_doc_ids),
        technical_feasibility=_normalize_findings(report.technical_feasibility, valid_doc_ids),
        customer_validation=_normalize_findings(report.customer_validation, valid_doc_ids),
        opportunities=_normalize_findings(report.opportunities, valid_doc_ids),
        risks=_normalize_findings(report.risks, valid_doc_ids),
        recommendations=report.recommendations,
        kpis=report.kpis,
        roadmap=report.roadmap,
    )


def complete_report(
    report: StrategyReport,
    state: GraphState,
    docs: list[SourceDocument],
) -> StrategyReport:
    logger.debug("Completing Strategy Report missing sections")
    base = _build_evidence_report(state, docs)
    return StrategyReport(
        executive_summary=report.executive_summary or base.executive_summary,
        findings=report.findings or base.findings,
        market_analysis=report.market_analysis or base.market_analysis,
        competitor_landscape=report.competitor_landscape or base.competitor_landscape,
        technical_feasibility=report.technical_feasibility or base.technical_feasibility,
        customer_validation=report.customer_validation or base.customer_validation,
        opportunities=report.opportunities or base.opportunities,
        risks=report.risks or base.risks,
        recommendations=report.recommendations or base.recommendations,
        kpis=report.kpis or base.kpis,
        roadmap=report.roadmap or base.roadmap,
    )


def _normalize_findings(findings: list[Finding], valid_doc_ids: set[str]) -> list[Finding]:
    logger.debug("Normalizing Strategy Report findings")
    return [_normalize_finding(finding, valid_doc_ids) for finding in findings]


def _normalize_finding(finding: Finding, valid_doc_ids: set[str]) -> Finding:
    logger.debug("Normalizing one Strategy Report finding")
    citations = [
        citation
        for citation in finding.citations
        if citation.doc_id in valid_doc_ids and citation.quote_or_paraphrase.strip()
    ]
    statement = finding.statement.strip()
    if not citations and not statement.startswith("UNVERIFIED:"):
        statement = f"UNVERIFIED: {statement}"
    return Finding(statement=statement, citations=citations)


def _finding_from_doc(doc: SourceDocument, prefix: str = "Evidence signal") -> Finding:
    logger.debug("Building finding from source document %s", doc.doc_id)
    return Finding(
        statement=f"{prefix}: {doc.title}",
        citations=[
            Citation(
                doc_id=doc.doc_id,
                quote_or_paraphrase=_truncate(doc.content, 220),
            )
        ],
    )


def _source_context(docs: list[SourceDocument]) -> list[dict[str, str | None]]:
    logger.debug("Building Strategy Engine source context")
    return [
        {
            "doc_id": doc.doc_id,
            "agent": doc.agent,
            "title": doc.title,
            "source_url": str(doc.source_url) if doc.source_url else None,
            "content": _truncate(doc.content, MAX_DOC_CHARS),
        }
        for doc in docs
    ]


def _strategy_query(state: GraphState) -> str:
    logger.debug("Building Strategy Engine query")
    if state.intent is None:
        return state.idea_raw
    return " ".join(
        part
        for part in (
            state.intent.idea_raw,
            state.intent.industry,
            state.intent.target_audience,
            state.intent.problem_statement,
            state.intent.proposed_solution,
            " ".join(state.intent.data_needs),
        )
        if part
    )


def build_executive_summary(
    state: GraphState,
    docs: list[SourceDocument],
) -> str:
    logger.debug("Building executive summary")
    intent = state.intent
    if intent is None:
        return f"Research summary for {state.idea_raw} based on {len(docs)} retrieved sources."

    counts = {
        "competitor": sum(1 for doc in docs if doc.agent == "competitor"),
        "paper": sum(1 for doc in docs if doc.agent == "paper"),
        "trend": sum(1 for doc in docs if doc.agent == "trend"),
    }
    return (
        f"This report evaluates '{intent.idea_raw}' for {intent.target_audience} in "
        f"{intent.industry}. It is grounded in {len(docs)} retrieved source documents: "
        f"{counts['competitor']} competitor signals, {counts['paper']} technical/research "
        f"signals, and {counts['trend']} trend signals. The core problem assessed is: "
        f"{intent.problem_statement}. The proposed solution assessed is: "
        f"{intent.proposed_solution}."
    )


def _looks_like_uncertainty(doc: SourceDocument) -> bool:
    logger.debug("Checking uncertainty keywords for %s", doc.doc_id)
    lowered = f"{doc.title} {doc.content}".lower()
    return any(
        keyword in lowered
        for keyword in (
            "not run",
            "risk",
            "challenge",
            "regulatory",
            "privacy",
            "security",
            "uncertain",
        )
    )


def _truncate(value: str, max_chars: int) -> str:
    logger.debug("Truncating Strategy Engine text")
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."
