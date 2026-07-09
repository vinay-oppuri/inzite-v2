"""Typed contracts for every hop in the pipeline.

Nothing free-text moves between graph nodes. Every LLM call is asked to
return one of these shapes, and every shape is validated before the next
node reads it. This is the single most important file in the repo for
avoiding the "fabricated ATS score" class of bug.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Intent parsing
# ---------------------------------------------------------------------------

class BusinessModel(str, Enum):
    b2b_saas = "b2b_saas"
    b2c = "b2c"
    marketplace = "marketplace"
    hardware = "hardware"
    api_platform = "api_platform"
    other = "other"


class StartupIntent(BaseModel):
    """Structured extraction of the user's raw idea."""

    idea_raw: str
    industry: str
    target_audience: str
    business_model: BusinessModel
    problem_statement: str
    proposed_solution: str
    data_needs: list[str] = Field(default_factory=list)
    agent_triggers: list[Literal["competitor", "paper", "trend"]] = Field(
        default_factory=lambda: ["competitor", "paper", "trend"]
    )


# ---------------------------------------------------------------------------
# Task planning
# ---------------------------------------------------------------------------

class ResearchTask(BaseModel):
    task_id: str
    agent: Literal["competitor", "paper", "trend"]
    query: str
    priority: int = 1


class TaskPlan(BaseModel):
    intent: StartupIntent
    tasks: list[ResearchTask]


# ---------------------------------------------------------------------------
# Agent outputs - every agent returns this exact shape
# ---------------------------------------------------------------------------

class SourceDocument(BaseModel):
    """One retrievable unit of evidence. Everything downstream cites this,
    never raw model output."""

    doc_id: str
    source_url: HttpUrl | None = None
    title: str
    content: str
    published_at: datetime | None = None
    agent: Literal["competitor", "paper", "trend"]


class AgentResult(BaseModel):
    success: bool
    agent: Literal["competitor", "paper", "trend"]
    output_summary: str
    output_raw_docs: list[SourceDocument]
    error: str | None = None


# ---------------------------------------------------------------------------
# Strategy synthesis - every claim must carry a citation
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    doc_id: str
    quote_or_paraphrase: str


class Finding(BaseModel):
    statement: str
    citations: list[Citation] = Field(
        default_factory=list,
        description="Empty citations list is a signal this claim is unverified "
        "and should be flagged, not presented as fact.",
    )


class StrategyReport(BaseModel):
    executive_summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    market_analysis: list[Finding] = Field(default_factory=list)
    competitor_landscape: list[Finding] = Field(default_factory=list)
    technical_feasibility: list[Finding] = Field(default_factory=list)
    customer_validation: list[Finding] = Field(default_factory=list)
    opportunities: list[Finding] = Field(default_factory=list)
    risks: list[Finding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    kpis: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Graph state - the object LangGraph threads through every node
# ---------------------------------------------------------------------------

class GraphState(BaseModel):
    run_id: str
    idea_raw: str
    intent: StartupIntent | None = None
    plan: TaskPlan | None = None
    agent_results: list[AgentResult] = Field(default_factory=list)
    retrieved_docs: list[SourceDocument] = Field(default_factory=list)
    strategy: StrategyReport | None = None
    final_report_markdown: str | None = None
    error_log: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API/job state - shared by routes and the lightweight local worker
# ---------------------------------------------------------------------------

class ResearchRunRecord(BaseModel):
    run_id: str
    idea_raw: str
    status: Literal["queued", "running", "completed", "failed"]
    final_report_markdown: str | None = None
    error_log: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
