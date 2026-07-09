from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.app.config import get_settings

logger = logging.getLogger(__name__)


def save_run_artifacts(run_id: str, result: dict[str, Any]) -> Path:
    """Save reviewable research artifacts for a completed run."""

    logger.info("Saving artifacts for run %s", run_id)
    settings = get_settings()
    run_dir = Path(settings.artifact_root) / run_id
    latest_dir = Path(settings.artifact_root) / "latest"
    raw_docs_dir = Path(settings.raw_docs_root) / run_id

    raw_docs = to_jsonable(result.get("retrieved_docs", []))
    agent_summaries = to_jsonable(result.get("agent_results", []))
    strategy_report = to_jsonable(result.get("strategy"))
    final_report_markdown = str(result.get("final_report_markdown") or "")
    final_report = build_final_report_payload(run_id, result)

    for directory in (run_dir, latest_dir):
        directory.mkdir(parents=True, exist_ok=True)
        write_json(directory / "raw_docs.json", raw_docs)
        write_json(directory / "agent_summaries.json", agent_summaries)
        write_json(directory / "strategy_report.json", strategy_report)
        write_text(directory / "final_report.md", final_report_markdown)
        write_json(directory / "final_report.json", final_report)

    raw_docs_dir.mkdir(parents=True, exist_ok=True)
    write_json(raw_docs_dir / "raw_docs.json", raw_docs)

    return run_dir


def build_final_report_payload(run_id: str, result: dict[str, Any]) -> dict[str, Any]:
    logger.debug("Building final report artifact payload for run %s", run_id)
    return {
        "run_id": run_id,
        "idea_raw": to_jsonable(result.get("idea_raw")),
        "intent": to_jsonable(result.get("intent")),
        "plan": to_jsonable(result.get("plan")),
        "agent_results": to_jsonable(result.get("agent_results", [])),
        "raw_docs": to_jsonable(result.get("retrieved_docs", [])),
        "strategy_report": to_jsonable(result.get("strategy")),
        "final_report_markdown": result.get("final_report_markdown") or "",
        "error_log": to_jsonable(result.get("error_log", [])),
    }


def write_json(path: Path, payload: Any) -> None:
    logger.debug("Writing JSON artifact %s", path)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def write_text(path: Path, payload: str) -> None:
    logger.debug("Writing text artifact %s", path)
    path.write_text(payload, encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    logger.debug("Converting value to JSON artifact payload")
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value
