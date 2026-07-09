# AGENTS.md - apps/services

This file is the handoff guide for agents working inside `apps/services`. Keep it current when the service architecture, commands, environment variables, or provider choices change.

## Service Summary

`apps/services` is a FastAPI backend for an agentic startup research assistant. A user submits a startup idea, the service turns it into a typed intent, creates a research plan, runs specialist research agents concurrently, synthesizes a detailed citation-aware strategy report, and supports follow-up chat over the completed run context.

The service is intentionally simple and strict:

- FastAPI exposes the HTTP API.
- LangGraph is the only orchestrator.
- Pydantic models in `src/core/schemas.py` are the only cross-node data contracts.
- Groq is used for structured LLM generation.
- External data sources are wrapped with retry logic.
- Tests must not depend on real API keys or live network calls.
- Qdrant indexing is optional and disabled by default.

## Current Provider Choices

- LLM provider: Groq.
- LLM wrapper: `src/core/llm/groq_client.py`.
- Structured output method: Groq OpenAI-compatible chat completions with JSON Schema response format.
- Qwen models use JSON Object mode directly and validate locally with Pydantic.
- For non-Qwen models, if Groq JSON Schema mode returns `json_validate_failed`, the client retries the same prompt once through JSON Object mode and validates locally.
- Embeddings: Groq does not currently expose a text embeddings endpoint in the official API reference. The service therefore uses deterministic local vectors in `src/core/rag/embeddings.py` when `ENABLE_RAG_INDEXING=true`.
- Vector store: Qdrant, opt-in only.
- Checkpoint store: Postgres LangGraph checkpointer, opt-in only.

## Required Runtime Environment

Copy `.env.example` to `.env` inside `apps/services`.

Minimum real run variables:

```env
GROQ_API_KEY=your_groq_key
GROQ_MODEL=qwen/qwen3-32b

TAVILY_API_KEY=your_tavily_key
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key
NEWS_API_KEY=

DISABLE_LIVE_CALLS=false
ENABLE_KEYLESS_LIVE_SOURCES=false

ARTIFACT_ROOT=data/memory_store
RAW_DOCS_ROOT=data/raw_docs
ENFORCE_INTERNAL_API_KEY=false
INTERNAL_API_KEY=change-this-in-production

ENABLE_RAG_INDEXING=false
EMBEDDING_PROVIDER=local
EMBEDDING_DIMENSIONS=384

ENABLE_POSTGRES_CHECKPOINTS=false
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/research_agent
REDIS_URL=redis://localhost:6379/0
```

Optional observability variables:

```env
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

Important: never commit `.env` or any real API key.

## Commands

Run from `apps/services`.

Install/sync dependencies:

```bash
uv sync
```

Start FastAPI locally:

```bash
uv run uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000
```

Equivalent npm script:

```bash
npm run dev
```

Start local infrastructure:

```bash
docker compose up -d postgres qdrant redis
```

Equivalent Make target:

```bash
make up
```

Run tests:

```bash
uv run pytest
```

Run local eval harness:

```bash
uv run python run_evals.py
```

Compile check:

```bash
uv run python -m compileall src run_evals.py
```

## FastAPI Endpoints

- `GET /` returns a welcome message.
- `GET /health` returns service health and environment.
- `POST /research` enqueues a background research run and returns a run record with status `queued`.
- `POST /research/sync` runs the graph inline and returns the completed run record. Use this for manual local testing.
- `GET /research/{run_id}` returns a run record.
- `GET /research/{run_id}/events` streams run status updates over SSE.
- `POST /chat` answers a follow-up question from retrieved context for a completed run.

## Saved Run Artifacts

Every completed `/research` or `/research/sync` run saves review files locally.

Run-specific folder:

```text
data/memory_store/{run_id}/
```

Latest-run convenience folder:

```text
data/memory_store/latest/
```

Raw-docs mirror:

```text
data/raw_docs/{run_id}/raw_docs.json
```

Files saved for each run:

- `raw_docs.json`: all retrieved `SourceDocument` evidence.
- `agent_summaries.json`: full `AgentResult` outputs from each research agent.
- `strategy_report.json`: structured `StrategyReport` before Markdown rendering.
- `final_report.md`: human-readable research report.
- `final_report.json`: complete review payload with intent, plan, docs, strategy, report, and errors.

These generated folders are ignored by git through `data/`.

Manual sync test:

```powershell
$body = @{
  idea = "AI copilot for job seekers that tailors resumes and finds matching jobs"
} | ConvertTo-Json

$result = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/research/sync" `
  -ContentType "application/json" `
  -Body $body

$result.status
$result.error_log
$result.final_report_markdown
```

Follow-up chat test:

```powershell
$chat = @{
  run_id = $result.run_id
  question = "Who are the main competitors and risks?"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body $chat
```

## Directory Map

```text
src/app/                 FastAPI app, routes, config, worker, DB models
src/app/api/             HTTP route modules
src/agents/              Specialist research agents
src/core/                Shared graph, schemas, retry, RAG, LLM wrapper
src/core/graph/          LangGraph builder and node functions
src/core/graph/nodes/    Pipeline stages
src/core/llm/            Groq structured-generation client
src/core/rag/            Optional retrieval/indexing helpers
tests/                   Offline unit, graph, API, and synthesis tests
run_evals.py             Offline eval harness with local doubles by default
eval_set.json            Startup ideas and expected agent triggers
docker-compose.yml       Local Postgres, Qdrant, Redis, API stack
```

## Production Data And Auth Decision

- PostgreSQL is the relational database for app data: Better Auth tables,
  users, research runs, reports, chat sessions, and optional LangGraph
  checkpoints.
- Qdrant is the vector database for embeddings and similarity search payloads.
  Keep it separate from Postgres in production.
- Redis is reserved for cache/queue work.
- Better Auth belongs in `apps/dashboard`, because it is a TypeScript auth
  server/client and owns browser cookies.
- Sign-in and sign-up UI belongs in `apps/dashboard`.
- FastAPI should be private. Dashboard server routes validate the Better Auth
  session, then call FastAPI with `x-internal-api-key`.
- In production set `ENFORCE_INTERNAL_API_KEY=true` in services and set the same
  secret as `SERVICES_INTERNAL_API_KEY` in dashboard.

## Data Contracts

All cross-node and cross-agent objects live in `src/core/schemas.py`.

- `BusinessModel`: enum for parsed startup business model.
- `StartupIntent`: structured result of intent parsing.
- `ResearchTask`: one agent-specific task.
- `TaskPlan`: list of planned research tasks.
- `SourceDocument`: one cited source/evidence unit.
- `AgentResult`: exact output contract for every research agent.
- `Citation`: reference to a real `SourceDocument.doc_id`.
- `Finding`: a claim with citations; empty citations mean unverified.
- `StrategyReport`: findings, opportunities, risks, recommendations, KPIs, roadmap.
- `StrategyReport` also includes executive summary, market analysis, competitor landscape, technical feasibility, and customer validation sections.
- `GraphState`: state object threaded through LangGraph.
- `ResearchRunRecord`: API/job status record.

Do not create duplicate Pydantic models in node or route files. If a new shape crosses a boundary, add it to `src/core/schemas.py` first.

## Graph Flow

The graph is built in `src/core/graph/builder.py`.

Pipeline order:

1. `intent_parser_node`
2. `task_planner_node`
3. `research_fanout_node`
4. `rag_index_node`
5. `strategy_engine_node`
6. `report_builder_node`

The graph compiles with a Postgres checkpointer only when `ENABLE_POSTGRES_CHECKPOINTS=true`. If checkpointing is enabled but cannot initialize, startup should fail loudly.

## Graph Nodes

`intent_parser.py`

- Reads `GraphState.idea_raw`.
- Calls `generate_structured()` from `src/core/llm/groq_client.py`.
- Produces `StartupIntent`.
- Raises on empty idea or missing/disabled LLM configuration.

`task_planner.py`

- Reads `StartupIntent`.
- Creates one `ResearchTask` per triggered agent.
- Builds clean deterministic queries for `competitor`, `paper`, and `trend`.

`research_fanout.py`

- Runs planned tasks concurrently with `asyncio.gather`.
- Dispatches via `AGENT_REGISTRY`.
- Converts each agent failure into `AgentResult(success=False)` and appends to `error_log`.
- A single failed agent must not crash the graph.

`rag_index.py`

- Optional side-effect node.
- Runs only when `ENABLE_RAG_INDEXING=true`, there are retrieved docs, and live calls are not disabled.
- Uses local deterministic embeddings from `src/core/rag/embeddings.py`.
- Upserts vectors to Qdrant via `src/core/rag/qdrant_store.py`.
- Per-doc embedding failures and Qdrant failures are logged in `error_log`.

`strategy_engine.py`

- Retrieves/reranks docs with local BM25 and overlap scoring.
- Uses Groq structured generation when `GROQ_API_KEY` exists, live calls are enabled, and context docs exist.
- Produces detailed market, competitor, technical, customer-validation, opportunity, risk, KPI, and roadmap content.
- Enforces that generated citations reference real retrieved `doc_id` values.
- If Groq synthesis fails, creates a deterministic evidence report and logs the synthesis failure.

`report_builder.py`

- Deterministically renders `StrategyReport` to Markdown.
- Renders a full research document with executive summary, startup brief, methodology, detailed sections, evidence matrix, sources, and run notes.
- Does not call an LLM.

## Agents

All agents subclass `BaseResearchAgent` from `src/agents/base.py` and return `AgentResult`.

`competitor_scout.py`

- Agent name: `competitor`.
- Requires `TAVILY_API_KEY`.
- Uses Tavily for competitors, alternatives, positioning signals.
- Produces competitor `SourceDocument`s.
- No LLM calls.

`paper_miner.py`

- Agent name: `paper`.
- Uses Semantic Scholar Graph API.
- Requires `SEMANTIC_SCHOLAR_API_KEY` unless `ENABLE_KEYLESS_LIVE_SOURCES=true`.
- Sends a `User-Agent` header.
- Produces technical/research `SourceDocument`s.
- No LLM calls.

`tech_paper_miner.py`

- Compatibility alias for `PaperMinerAgent`.
- Exports `PaperMinerAgent` and `TechPaperMinerAgent`.

`trend_scraper.py`

- Agent name: `trend`.
- Uses NewsAPI, Reddit public JSON, and/or Tavily depending on configuration.
- Partial source failures are allowed when at least one trend source returns documents.
- Raises only when no trend source is configured or all configured sources fail.
- No LLM calls.

## External Calls And Retry Rules

All retryable external calls use `resilient_call()` from `src/core/retry.py`.

Wrapped calls include:

- Groq chat completions in `src/core/llm/groq_client.py`.
- Tavily competitor search in `src/agents/competitor_scout.py`.
- Semantic Scholar paper search in `src/agents/paper_miner.py`.
- NewsAPI, Reddit, and Tavily trend searches in `src/agents/trend_scraper.py`.
- Qdrant collection creation and point upsert in `src/core/rag/qdrant_store.py`.

Use `ExternalAPIError` for retryable external failures.

## RAG Folder Responsibilities

`src/core/rag/embeddings.py`

- Local deterministic vector generation.
- Used only by optional Qdrant indexing.

`src/core/rag/qdrant_store.py`

- Qdrant collection creation, payload building, and document upsert.

`src/core/rag/retriever.py`

- Local BM25 retrieval over current run `SourceDocument`s.

`src/core/rag/reranker.py`

- Lightweight query/document overlap reranking.

Keep RAG files focused on retrieval/indexing. Do not put graph orchestration, API routes, or agent-specific scraping logic in this folder.

## App Layer

`src/app/config.py`

- Single settings source using `pydantic-settings`.
- No scattered `os.environ.get()` in production code.

`src/app/main.py`

- Creates FastAPI app.
- Registers routers.
- Provides `/` and `/health`.
- Enforces `x-internal-api-key` when `ENFORCE_INTERNAL_API_KEY=true`.

`src/app/api/routes_research.py`

- Research run endpoints.
- Uses `worker.py` to enqueue or run graph.

`src/app/api/routes_chat.py`

- Follow-up Q&A endpoint.
- Uses completed run docs from `worker.py`.
- Local relevance ranking only; no LLM call yet.

`src/app/worker.py`

- In-memory run store for current local implementation.
- Builds and invokes the LangGraph app.
- Stores retrieved docs and final report in process memory.
- Saves per-run review artifacts through `src/app/artifacts.py`.
- Not durable across process restarts.

`src/app/artifacts.py`

- Writes `raw_docs.json`, `agent_summaries.json`, `strategy_report.json`, `final_report.md`, and `final_report.json`.
- Saves both run-specific artifacts and a `latest` copy for quick manual review.
- Mirrors raw docs into `RAW_DOCS_ROOT`.

`src/app/db_models.py`

- SQLAlchemy models for future persistence: `ResearchRun`, `Report`, `ChatSession`.
- Separate from LangGraph checkpoint tables.
- Better Auth owns the primary user table in dashboard/Postgres. Service
  persistence stores Better Auth user IDs as strings instead of creating a
  second identity system.

## Testing Rules

Required tests are offline and deterministic.

- `tests/conftest.py` disables live calls and clears API keys by default.
- `mock_groq_intent` replaces Groq structured parsing in graph/API tests.
- `mock_agent_registry` replaces real agents for end-to-end smoke/API tests.
- Agent tests monkeypatch network functions directly and validate parsing behavior.
- `run_evals.py` uses local eval doubles by default. `--live` is the only path that should call real providers.

Test files:

- `test_schemas.py`: schema construction and validation behavior.
- `test_intent_parser.py`: Groq structured parser boundary.
- `test_task_planner.py`: deterministic planning.
- `test_agents.py`: per-agent parsing and config failures.
- `test_graph_smoke.py`: full graph with mocked intent and agents.
- `test_strategy_engine.py`: citation enforcement/report rendering.
- `test_api.py`: FastAPI sync research and chat endpoints.

## Manual Live Testing Checklist

For a real no-error FastAPI run:

1. Add `.env` with `GROQ_API_KEY`, `TAVILY_API_KEY`, and `SEMANTIC_SCHOLAR_API_KEY`.
2. Keep `DISABLE_LIVE_CALLS=false`.
3. Keep `ENABLE_RAG_INDEXING=false` for the simplest first run.
4. Start the API with `uv run uvicorn src.app.main:app --reload --host 127.0.0.1 --port 8000`.
5. POST a startup idea to `/research/sync`.
6. Confirm `status == "completed"`.
7. Confirm `error_log` is empty.
8. Confirm `final_report_markdown` includes findings and sources.
9. Use `/chat` only after the run is completed.

If `error_log` contains agent failures:

- Competitor failures usually mean `TAVILY_API_KEY` is missing/invalid.
- Tavily queries are capped before API calls because Tavily rejects queries over 400 characters.
- Paper failures usually mean `SEMANTIC_SCHOLAR_API_KEY` is missing/invalid or keyless calls are blocked.
- Semantic Scholar 429 rate limits are handled as a paper-agent partial result and should not appear in `error_log`.
- Trend failures usually mean no trend source is configured or all configured trend sources failed.
- Strategy synthesis failures usually mean `GROQ_API_KEY`, model choice, or Groq structured output response failed.

## Production Cautions

- Do not reintroduce rule-based or fake production fallbacks in `intent_parser.py` or `task_planner.py`.
- Do not silently fabricate citations.
- Do not let raw LLM text cross node boundaries.
- Do not introduce a second orchestrator.
- Do not make required tests depend on real API keys.
- Do not enable Qdrant indexing by default unless the embedding provider and vector store are production-ready.
- Do not commit `.env`, local data folders, logs, or generated cache files.
- Keep helper functions simple and typed where it clarifies contracts.

## Known Current Limitations

- `worker.py` uses in-memory storage, so runs disappear on process restart.
- `/research` background execution uses `asyncio.create_task`, not a durable queue.
- Redis is present in config/compose but not yet used as a real job queue.
- SQLAlchemy models exist, but API routes do not persist runs/reports to Postgres yet.
- Langfuse settings exist, but tracing is not yet wired around graph invocations.
- `/chat` uses local retrieved docs from the in-memory run result and does not yet query Qdrant.
- Groq embeddings are not available through an official endpoint; optional indexing uses local vectors.

## Dependency Notes

Python requirement: `>=3.13`.

Primary dependencies:

- `fastapi`, `uvicorn`
- `langgraph`
- `pydantic`, `pydantic-settings`
- `httpx`
- `tenacity`
- `tavily-python`
- `rank-bm25`
- `qdrant-client`
- `sqlalchemy[asyncio]`, `asyncpg`
- `redis`
- `langfuse`
- `pytest`, `pytest-asyncio` for dev tests

`uv.lock` may include transitive packages that are not imported directly by service code.

## Commit Grouping Suggestions

Useful commit slices:

- `feat: add production research agents`
  - `src/agents/base.py`
  - `src/agents/competitor_scout.py`
  - `src/agents/paper_miner.py`
  - `src/agents/trend_scraper.py`
  - `src/agents/tech_paper_miner.py`

- `feat: wire production research graph`
  - `src/core/schemas.py`
  - `src/core/graph/**`
  - `src/core/llm/groq_client.py`
  - `src/core/rag/**`
  - `src/core/retry.py`
  - `src/core/checkpoint.py`

- `feat: add service api and worker`
  - `src/app/**`
  - `.env.example`
  - `Dockerfile`
  - `docker-compose.yml`
  - `Makefile`
  - `README.md`
  - `AGENTS.md`

- `test: add mocked service tests and evals`
  - `tests/**`
  - `eval_set.json`
  - `run_evals.py`
  - `package.json`
  - `pyproject.toml`
  - `uv.lock`

- `chore: remove legacy service modules`
  - deleted legacy `src/core/intent_parser.py`
  - deleted legacy `src/core/orchestrator.py`
  - deleted legacy `src/core/pipeline.py`
  - deleted legacy `src/core/planner.py`
  - deleted legacy `src/core/llm/gemini_client.py`
  - deleted legacy `src/schemas/**`
