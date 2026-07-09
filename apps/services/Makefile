.PHONY: dev up down test compile

dev:
	uv run uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000

up:
	docker compose up -d postgres qdrant redis

down:
	docker compose down

test:
	uv run pytest -q

compile:
	uv run python -m compileall src tests
