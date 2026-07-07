from __future__ import annotations

from src.core.schemas import GraphState, ResearchTask, StartupIntent, TaskPlan

TECHNICAL_DATA_NEED = "technical feasibility evidence"


async def task_planner_node(state: GraphState) -> dict:
    """Turn a validated StartupIntent into executable research tasks.

    This phase is intentionally deterministic: one targeted query per
    triggered agent.
    """
    assert state.intent is not None, "intent_parser_node must run first"

    tasks = [
        ResearchTask(
            task_id=f"{agent}-{index}",
            agent=agent,
            query=_build_query(state.intent, agent),
            priority=_priority_for_agent(state.intent, agent),
        )
        for index, agent in enumerate(state.intent.agent_triggers, start=1)
    ]

    return {"plan": TaskPlan(intent=state.intent, tasks=tasks)}


def _build_query(intent: StartupIntent, agent: str) -> str:
    data_needs = ", ".join(intent.data_needs)

    if agent == "competitor":
        return _compact(
            f"Find competitors, substitutes, and positioning for {intent.proposed_solution} "
            f"serving {intent.target_audience} in {intent.industry}. "
            f"Customer problem: {intent.problem_statement}."
        )

    if agent == "paper":
        return _compact(
            f"Find technical papers, methods, benchmarks, and implementation evidence "
            f"for {intent.proposed_solution}. Audience: {intent.target_audience}. "
            f"Problem: {intent.problem_statement}. "
            f"Evidence needs: {data_needs}."
        )

    return _compact(
        f"Find market, news, community, and adoption trend signals for {intent.proposed_solution} "
        f"in {intent.industry}. Audience: {intent.target_audience}. "
        f"Problem: {intent.problem_statement}. "
        f"Evidence needs: {data_needs}."
    )


def _priority_for_agent(intent: StartupIntent, agent: str) -> int:
    if agent == "paper" and TECHNICAL_DATA_NEED in intent.data_needs:
        return 1
    if agent == "competitor":
        return 1
    if agent == "trend":
        return 2
    return 3


def _compact(value: str) -> str:
    return " ".join(value.split())
