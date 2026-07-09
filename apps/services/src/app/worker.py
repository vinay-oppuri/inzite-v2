from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from src.app.artifacts import save_run_artifacts
from src.core.graph.builder import build_graph
from src.core.schemas import GraphState, ResearchRunRecord, SourceDocument

logger = logging.getLogger(__name__)

_graph = build_graph()
_runs: dict[str, ResearchRunRecord] = {}
_run_results: dict[str, dict[str, Any]] = {}


def enqueue_research_run(idea_raw: str) -> ResearchRunRecord:
    logger.info("Queueing research run")
    run_id = str(uuid.uuid4())
    record = ResearchRunRecord(run_id=run_id, idea_raw=idea_raw, status="queued")
    _runs[run_id] = record
    asyncio.create_task(_execute_research_run(run_id, idea_raw))
    return record


async def run_research_now(idea_raw: str, run_id: str | None = None) -> ResearchRunRecord:
    logger.info("Running sync research request")
    run_id = run_id or str(uuid.uuid4())
    _runs[run_id] = ResearchRunRecord(run_id=run_id, idea_raw=idea_raw, status="queued")
    await _execute_research_run(run_id, idea_raw)
    return _runs[run_id]


def get_research_run(run_id: str) -> ResearchRunRecord | None:
    logger.debug("Reading research run %s", run_id)
    return _runs.get(run_id)


def get_retrieved_docs(run_id: str) -> list[SourceDocument]:
    logger.debug("Reading retrieved docs for run %s", run_id)
    result = _run_results.get(run_id)
    if not result:
        return []
    docs = result.get("retrieved_docs", [])
    parsed_docs: list[SourceDocument] = []
    for doc in docs:
        if isinstance(doc, SourceDocument):
            parsed_docs.append(doc)
        elif isinstance(doc, dict):
            parsed_docs.append(SourceDocument.model_validate(doc))
    return parsed_docs


async def _execute_research_run(run_id: str, idea_raw: str) -> None:
    logger.info("Starting research run %s", run_id)
    _update_run(run_id, status="running")
    try:
        initial_state = GraphState(run_id=run_id, idea_raw=idea_raw)
        result = await _graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": run_id}},
        )
        _run_results[run_id] = result
        error_log = list(result.get("error_log", []))

        try:
            artifact_dir = save_run_artifacts(run_id, result)
            logger.info("Saved research artifacts for run %s to %s", run_id, artifact_dir)
        except Exception as exc:  # noqa: BLE001 - artifact writes should not hide the report
            logger.exception("Artifact save failed for run %s", run_id)
            error_log.append(f"artifact save failed: {exc}")
            result["error_log"] = error_log

        _update_run(
            run_id,
            status="completed",
            final_report_markdown=result.get("final_report_markdown"),
            error_log=error_log,
        )
        logger.info("Completed research run %s", run_id)
    except Exception as exc:  # noqa: BLE001 - job failure boundary
        logger.exception("Research run %s failed", run_id)
        _update_run(run_id, status="failed", error_log=[str(exc)])


def _update_run(
    run_id: str,
    *,
    status: str,
    final_report_markdown: str | None = None,
    error_log: list[str] | None = None,
) -> None:
    logger.debug("Updating run %s status to %s", run_id, status)
    existing = _runs[run_id]
    _runs[run_id] = existing.model_copy(
        update={
            "status": status,
            "final_report_markdown": final_report_markdown
            if final_report_markdown is not None
            else existing.final_report_markdown,
            "error_log": error_log if error_log is not None else existing.error_log,
            "updated_at": datetime.now(timezone.utc),
        }
    )
