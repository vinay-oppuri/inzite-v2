from __future__ import annotations

import logging

from fastapi import FastAPI

from src.app.api.routes_chat import router as chat_router
from src.app.api.routes_research import router as research_router
from src.app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Startup Research Agent",
    description="Agentic research assistant that turns a startup idea into a grounded strategy report.",
    version="0.1.0",
)

app.include_router(research_router)
app.include_router(chat_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to the Startup Research Agent API."}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
