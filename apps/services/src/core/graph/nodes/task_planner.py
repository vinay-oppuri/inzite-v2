from typing import Literal

from src.core.schemas import GraphState, ResearchTask, StartupIntent, TaskPlan


async def task_planner_node(state: GraphState) -> dict:
    """
    Creates research tasks based on the agents selected
    by the intent parser.
    """

    if state.intent is None:
        raise ValueError("intent_parser_node must run first")

    intent = state.intent
    tasks: list[ResearchTask] = []

    for index, agent in enumerate(intent.agent_triggers, start=1):
        task = ResearchTask(
            task_id=f"{agent}-{index}",
            agent=agent,
            query=build_query(intent, agent),
            priority=get_priority(intent, agent),
        )
        tasks.append(task)

    plan = TaskPlan(
        intent=intent,
        tasks=tasks,
    )

    return {"plan": plan}


def build_query(
    intent: StartupIntent,
    agent: Literal["competitor", "paper", "trend"],
) -> str:
    """
    Creates the search query for each research agent.
    """

    if agent == "competitor":
        query = (
            f"Find competitors and alternative solutions for "
            f"{intent.proposed_solution}. "
            f"Target audience: {intent.target_audience}. "
            f"Industry: {intent.industry}. "
            f"Problem: {intent.problem_statement}."
        )

    elif agent == "paper":
        data_needs = ", ".join(intent.data_needs)

        query = (
            f"Find technical papers, methods, benchmarks, and "
            f"implementation evidence for {intent.proposed_solution}. "
            f"Target audience: {intent.target_audience}. "
            f"Problem: {intent.problem_statement}. "
            f"Evidence needed: {data_needs}."
        )

    else:
        data_needs = ", ".join(intent.data_needs)

        query = (
            f"Find market trends, news, community discussions, "
            f"and adoption signals for {intent.proposed_solution}. "
            f"Industry: {intent.industry}. "
            f"Target audience: {intent.target_audience}. "
            f"Problem: {intent.problem_statement}. "
            f"Evidence needed: {data_needs}."
        )

    return " ".join(query.split())


def get_priority(
    intent: StartupIntent,
    agent: Literal["competitor", "paper", "trend"],
) -> int:
    """
    Assigns priority to each research agent.

    Lower number = higher priority.
    """

    if agent == "competitor":
        return 1

    if (
        agent == "paper"
        and "technical feasibility evidence" in intent.data_needs
    ):
        return 1

    if agent == "trend":
        return 2

    return 3
