# Startup Research Agent Service

FastAPI service for a multi-agent startup research pipeline orchestrated with LangGraph.

Given a startup idea, the service:

1. Parses the idea into validated Pydantic intent.
2. Builds an agent-specific research plan.
3. Fans out competitor, paper, and trend agents concurrently.
4. Collects cited `SourceDocument` evidence and optionally indexes it in Qdrant.
5. Synthesizes a citation-enforced strategy report with market, competitor, technical, customer, opportunity, risk, KPI, and roadmap sections.
6. Renders detailed deterministic Markdown and supports follow-up chat over completed run context.
7. Saves reviewable artifacts for each completed run.

Agents require their configured live sources and report clear failures through the graph when a source is unavailable. Live calls go through retry-wrapped helpers for Groq, Tavily, Semantic Scholar, NewsAPI, Reddit public JSON, and Qdrant.

## Local Development

```bash
cd apps/services
uv sync
uv run uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000
```

The API docs are available at `http://127.0.0.1:8000/docs`.

## Endpoints

- `GET /health` returns service status and environment.
- `POST /research` enqueues a background research run and returns a run record.
- `POST /research/sync` runs the graph inline for demos and tests.
- `GET /research/{run_id}` returns queued/running/completed/failed status.
- `GET /research/{run_id}/events` streams status changes with SSE.
- `POST /chat` answers follow-up questions from a completed run's retrieved context.

Example synchronous request:

```bash
curl -X POST http://127.0.0.1:8000/research/sync \
  -H "Content-Type: application/json" \
  -d "{\"idea\":\"AI copilot for job seekers\"}"
```

Completed runs save these files under `data/memory_store/{run_id}/` and
`data/memory_store/latest/`:

- `raw_docs.json`
- `agent_summaries.json`
- `strategy_report.json`
- `final_report.md`
- `final_report.json`

Raw documents are also mirrored to `data/raw_docs/{run_id}/raw_docs.json`.

## Project Layout

```text
src/app/          FastAPI entrypoint, API routes, local worker, DB models
src/core/         LangGraph builder, nodes, schemas, retry, retrieval, LLM wrapper
src/agents/       Specialist research agents
tests/            Offline unit, graph, API, and synthesis tests
```

## Environment

Copy `.env.example` to `.env` inside `apps/services` and fill in keys for live sources.

```text
GROQ_API_KEY=
GROQ_MODEL=qwen/qwen3-32b
ENABLE_RAG_INDEXING=false
EMBEDDING_PROVIDER=local
EMBEDDING_DIMENSIONS=384
TAVILY_API_KEY=
NEWS_API_KEY=
SEMANTIC_SCHOLAR_API_KEY=
ENABLE_KEYLESS_LIVE_SOURCES=false
DATABASE_URL=
ENABLE_POSTGRES_CHECKPOINTS=false
QDRANT_URL=
QDRANT_API_KEY=
REDIS_URL=
ARTIFACT_ROOT=data/memory_store
RAW_DOCS_ROOT=data/raw_docs
ENFORCE_INTERNAL_API_KEY=false
INTERNAL_API_KEY=
```

`ENABLE_KEYLESS_LIVE_SOURCES=true` allows no-auth sources such as Reddit public JSON and keyless Semantic Scholar. It is disabled by default so tests and local smoke runs never depend on live network access.

`ENABLE_RAG_INDEXING=false` keeps Qdrant indexing disabled for local runs. Groq does not expose a text embeddings endpoint, so the current local indexing path uses deterministic local vectors when indexing is explicitly enabled.

## Production Data And Auth

- PostgreSQL is the relational database for app data: users, research runs,
  reports, chat sessions, Better Auth tables, and LangGraph checkpoints when
  enabled.
- Qdrant is the vector database for retrieved document embeddings. Keep it
  separate from Postgres in production.
- Redis is reserved for cache/queue work.
- User authentication lives in `apps/dashboard` with Better Auth.
- FastAPI should be private behind the dashboard. In production, set
  `ENFORCE_INTERNAL_API_KEY=true` and share the same `INTERNAL_API_KEY` value
  with dashboard as `SERVICES_INTERNAL_API_KEY`.

Qdrant Cloud or secured self-hosted Qdrant can be configured with:

```env
QDRANT_URL=
QDRANT_API_KEY=
```

## Tests And Evals

```bash
cd apps/services
uv run pytest -q
uv run python run_evals.py
```

## Design Notes

- LangGraph is the single orchestrator.
- Every graph hop uses validated Pydantic models from `src/core/schemas.py`.
- Live external calls are isolated behind retry-wrapped helper functions.
- Groq structured generation lives behind `src/core/llm/groq_client.py`.
- Optional local embeddings live behind `src/core/rag/embeddings.py`.
- Findings, market analysis, competitor analysis, technical feasibility, customer validation, opportunities, and risks are citation-enforced. Unsupported claims are tagged `UNVERIFIED`.
- Postgres checkpointing and Qdrant indexing are opt-in so local development stays lightweight.
