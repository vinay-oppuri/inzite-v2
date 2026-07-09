import json

from src.app.artifacts import save_run_artifacts
from src.app.config import get_settings
from src.core.schemas import (
    AgentResult,
    Citation,
    Finding,
    SourceDocument,
    StrategyReport,
)


def test_save_run_artifacts_writes_review_files(tmp_path, monkeypatch):
    artifact_root = tmp_path / "memory_store"
    raw_docs_root = tmp_path / "raw_docs"
    monkeypatch.setenv("ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setenv("RAW_DOCS_ROOT", str(raw_docs_root))
    get_settings.cache_clear()

    doc = SourceDocument(
        doc_id="competitor-1",
        title="Competitor evidence",
        content="Competitors already offer job matching workflows.",
        agent="competitor",
    )
    result = {
        "run_id": "run-1",
        "idea_raw": "job search application for freshers",
        "retrieved_docs": [doc],
        "agent_results": [
            AgentResult(
                success=True,
                agent="competitor",
                output_summary="Found competitor evidence.",
                output_raw_docs=[doc],
            )
        ],
        "strategy": StrategyReport(
            executive_summary="Evidence-backed summary.",
            findings=[
                Finding(
                    statement="Competitor evidence exists.",
                    citations=[
                        Citation(
                            doc_id="competitor-1",
                            quote_or_paraphrase="Competitors already offer job matching workflows.",
                        )
                    ],
                )
            ],
        ),
        "final_report_markdown": "# Startup Research Report",
        "error_log": [],
    }

    run_dir = save_run_artifacts("run-1", result)

    for directory in (run_dir, artifact_root / "latest"):
        assert (directory / "raw_docs.json").exists()
        assert (directory / "agent_summaries.json").exists()
        assert (directory / "strategy_report.json").exists()
        assert (directory / "final_report.md").exists()
        assert (directory / "final_report.json").exists()

    raw_docs = json.loads((run_dir / "raw_docs.json").read_text(encoding="utf-8"))
    final_report = json.loads((run_dir / "final_report.json").read_text(encoding="utf-8"))

    assert raw_docs[0]["doc_id"] == "competitor-1"
    assert final_report["idea_raw"] == "job search application for freshers"
    assert (raw_docs_root / "run-1" / "raw_docs.json").exists()
