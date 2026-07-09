from __future__ import annotations

import asyncio
import logging

from src.agents.competitor_scout import CompetitorScoutAgent
from src.agents.paper_miner import PaperMinerAgent
from src.agents.trend_scraper import TrendScraperAgent
from src.core.schemas import AgentResult, GraphState, SourceDocument

logger = logging.getLogger(__name__)

AGENT_REGISTRY = {
    "competitor": CompetitorScoutAgent(),
    "paper": PaperMinerAgent(),
    "trend": TrendScraperAgent(),
}


async def research_fanout_node(state: GraphState) -> dict:
    """Runs every planned task concurrently via asyncio.gather, rather than
    sequentially - this is the fan-out step. A failed agent doesn't take
    down the run: its failure is captured as an AgentResult(success=False)
    and logged, and the graph continues with whatever succeeded.
    """
    if state.plan is None:
        raise ValueError("task_planner_node must run first")

    logger.info("Running Research Fanout with %s tasks", len(state.plan.tasks))

    async def run_task(task):
        logger.info("Running %s agent task %s", task.agent, task.task_id)
        agent = AGENT_REGISTRY[task.agent]
        try:
            return await agent.run(task)
        except Exception as exc:  # noqa: BLE001 - intentionally broad at the fan-out boundary
            logger.exception("%s agent task %s failed", task.agent, task.task_id)
            return AgentResult(
                success=False,
                agent=task.agent,
                output_summary="",
                output_raw_docs=[],
                error=str(exc),
            )

    results: list[AgentResult] = await asyncio.gather(
        *(run_task(task) for task in state.plan.tasks)
    )

    all_docs: list[SourceDocument] = []
    error_log = list(state.error_log)
    for result in results:
        if result.success:
            logger.info("%s agent completed with %s docs", result.agent, len(result.output_raw_docs))
            all_docs.extend(result.output_raw_docs)
        else:
            error_log.append(f"{result.agent} agent failed: {result.error}")

    return {
        "agent_results": results,
        "retrieved_docs": all_docs,
        "error_log": error_log,
    }
