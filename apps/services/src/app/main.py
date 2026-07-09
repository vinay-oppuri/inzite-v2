from __future__ import annotations

import hmac
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.app.api.routes_chat import router as chat_router
from src.app.api.routes_research import router as research_router
from src.app.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

app = FastAPI(
    title="Startup Research Agent",
    description="Agentic research assistant that turns a startup idea into a grounded strategy report.",
    version="0.1.0",
)

app.include_router(research_router)
app.include_router(chat_router)


@app.middleware("http")
async def require_internal_api_key(request: Request, call_next):
    logger.debug("Checking internal API key middleware")
    if not settings.enforce_internal_api_key or request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    received_key = request.headers.get("x-internal-api-key", "")
    expected_key = settings.internal_api_key

    if not expected_key or not hmac.compare_digest(received_key, expected_key):
        logger.warning("Rejected request with missing or invalid internal API key")
        return JSONResponse(
            status_code=401,
            content={"detail": "invalid internal API key"},
        )

    return await call_next(request)


@app.get("/")
def read_root() -> dict[str, str]:
    logger.info("Serving root endpoint")
    return {"message": "Welcome to the Startup Research Agent API."}


@app.get("/health")
async def health() -> dict[str, str]:
    logger.info("Serving health endpoint")
    return {"status": "ok", "env": settings.app_env}
