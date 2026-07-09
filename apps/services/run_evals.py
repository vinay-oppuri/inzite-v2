from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, Literal

from src.app.config import get_settings
from src.core.graph.builder import build_graph
from src.core.schemas import AgentResult, BusinessModel, GraphState, SourceDocument


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run startup research eval cases.")
    parser.add_argument("--eval-set", default="eval_set.json")
    parser.add_argument("--min-score", type=float, default=0.7)
    parser.add_argument("--live", action="store_true", help="Allow configured live API calls.")
    args = parser.parse_args()

    cases = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))

    if not args.live:
        _force_local_eval_mode()
        _install_local_eval_doubles(cases)

    graph = build_graph()
    results = []
    for case in cases:
        state = GraphState(run_id=str(uuid.uuid4()), idea_raw=case["idea"])
        result = await graph.ainvoke(state)
        score = _score_result(case, result)
        results.append(
            {
                "id": case["id"],
                "score": score,
                "status": "pass" if score >= args.min_score else "fail",
            }
        )

    print(json.dumps({"results": results}, indent=2))
    if any(item["score"] < args.min_score for item in results):
        raise SystemExit(1)


def _score_result(case: dict[str, Any], result: dict[str, Any]) -> float:
    score = 0.0
    if result.get("intent") is not None:
        score += 0.2
    if result.get("plan") is not None:
        expected_agents = set(case.get("expected_agents", []))
        actual_agents = {task.agent for task in result["plan"].tasks}
        if expected_agents <= actual_agents:
            score += 0.2
    if result.get("retrieved_docs"):
        score += 0.2
    strategy = result.get("strategy")
    if strategy and strategy.findings:
        cited = [finding for finding in strategy.findings if finding.citations]
        score += 0.2 * (len(cited) / len(strategy.findings))
    if result.get("final_report_markdown"):
        score += 0.2
    return round(score, 3)


def _install_local_eval_doubles(cases: list[dict[str, Any]]) -> None:
    from src.core.graph.nodes import intent_parser, research_fanout

    cases_by_idea = {case["idea"]: case for case in cases}

    async def generate_eval_intent(messages, schema):
        idea = _extract_startup_idea(messages)
        case = cases_by_idea.get(idea)
        if case is None:
            raise ValueError(f"No eval case found for startup idea: {idea}")

        return schema(
            idea_raw=idea,
            industry="unspecified",
            target_audience="unspecified",
            business_model=BusinessModel.other,
            problem_statement=f"Evaluate evidence for {idea}.",
            proposed_solution=idea,
            data_needs=[
                "competitor landscape",
                "technical feasibility evidence",
                "market trend signals",
            ],
            agent_triggers=case["expected_agents"],
        )

    class EvalAgent:
        def __init__(self, agent: Literal["competitor", "paper", "trend"]):
            self.agent = agent

        async def run(self, task):
            document = SourceDocument(
                doc_id=f"{task.task_id}-eval",
                title=f"{task.agent.title()} eval evidence",
                content=f"Eval evidence for {task.query}.",
                agent=task.agent,
            )
            return AgentResult(
                success=True,
                agent=task.agent,
                output_summary=f"{task.agent} eval completed.",
                output_raw_docs=[document],
            )

    intent_parser.generate_structured = generate_eval_intent
    research_fanout.AGENT_REGISTRY = {
        "competitor": EvalAgent("competitor"),
        "paper": EvalAgent("paper"),
        "trend": EvalAgent("trend"),
    }


def _extract_startup_idea(messages) -> str:
    for role, content in messages:
        if role == "human" and "Startup idea:" in content:
            return content.split("Startup idea:", 1)[1].strip()
    raise ValueError("Startup idea was not found in the intent prompt")


def _force_local_eval_mode() -> None:
    os.environ["DISABLE_LIVE_CALLS"] = "true"
    os.environ["GROQ_API_KEY"] = ""
    os.environ["TAVILY_API_KEY"] = ""
    os.environ["NEWS_API_KEY"] = ""
    os.environ["SEMANTIC_SCHOLAR_API_KEY"] = ""
    os.environ["ENABLE_KEYLESS_LIVE_SOURCES"] = "false"
    os.environ["ENABLE_POSTGRES_CHECKPOINTS"] = "false"
    os.environ["ENABLE_RAG_INDEXING"] = "false"
    get_settings.cache_clear()


if __name__ == "__main__":
    asyncio.run(main())
