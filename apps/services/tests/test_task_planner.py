import pytest

from src.core.graph.nodes.task_planner import task_planner_node
from src.core.schemas import BusinessModel, GraphState, StartupIntent


@pytest.mark.asyncio
async def test_task_planner_builds_agent_specific_queries():
    intent = StartupIntent(
        idea_raw="AI copilot for job seekers",
        industry="HR tech",
        target_audience="job seekers",
        business_model=BusinessModel.b2c,
        problem_statement="Job seekers spend too much time tailoring resumes.",
        proposed_solution="AI copilot for job seekers",
        data_needs=["competitor landscape", "technical feasibility evidence"],
    )
    state = GraphState(run_id="planner-test", idea_raw=intent.idea_raw, intent=intent)

    result = await task_planner_node(state)
    tasks = result["plan"].tasks

    assert [task.task_id for task in tasks] == ["competitor-1", "paper-2", "trend-3"]
    assert [task.agent for task in tasks] == ["competitor", "paper", "trend"]
    assert len({task.query for task in tasks}) == 3
    assert all("job seekers" in task.query for task in tasks)
    assert "competitors" in tasks[0].query.lower()
    assert "technical papers" in tasks[1].query.lower()
    assert "market trends" in tasks[2].query.lower()
    assert tasks[1].priority == 1


@pytest.mark.asyncio
async def test_task_planner_respects_trigger_subset():
    intent = StartupIntent(
        idea_raw="Compliance dashboard for finance teams",
        industry="fintech",
        target_audience="finance teams",
        business_model=BusinessModel.b2b_saas,
        problem_statement="Finance teams need faster compliance monitoring.",
        proposed_solution="Compliance dashboard",
        agent_triggers=["competitor", "trend"],
    )
    state = GraphState(run_id="planner-test", idea_raw=intent.idea_raw, intent=intent)

    result = await task_planner_node(state)

    assert [task.agent for task in result["plan"].tasks] == ["competitor", "trend"]
