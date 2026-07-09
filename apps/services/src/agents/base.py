from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from src.core.schemas import AgentResult, ResearchTask

logger = logging.getLogger(__name__)


class BaseResearchAgent(ABC):
    """Base contract for research agents."""

    agent_name: str

    @abstractmethod
    async def run(self, task: ResearchTask) -> AgentResult:
        """Run a research task and return structured evidence."""
        logger.debug("Running base research agent contract for task %s", task.task_id)

    def log_start(self, task: ResearchTask) -> None:
        logger.info("Running %s agent for task %s", self.agent_name, task.task_id)
