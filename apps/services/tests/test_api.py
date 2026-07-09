from fastapi.testclient import TestClient


def test_sync_research_endpoint_returns_completed_report(
    mock_groq_intent,
    mock_agent_registry,
):
    from src.app.main import app

    client = TestClient(app)

    response = client.post("/research/sync", json={"idea": "AI copilot for job seekers"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "AI copilot for job seekers" in payload["final_report_markdown"]
    assert payload["error_log"] == []


def test_chat_endpoint_answers_from_completed_run_context(
    mock_groq_intent,
    mock_agent_registry,
):
    from src.app.main import app

    client = TestClient(app)
    run = client.post("/research/sync", json={"idea": "AI copilot for job seekers"}).json()

    response = client.post(
        "/chat",
        json={"run_id": run["run_id"], "question": "What competitor evidence was found?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["citations"]
    assert "doc_id" in payload["citations"][0]
