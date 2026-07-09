from __future__ import annotations

import logging
from typing import Any

from src.app.config import get_settings

logger = logging.getLogger(__name__)


def get_postgres_checkpointer() -> Any | None:
    """Return a LangGraph Postgres checkpointer when explicitly enabled.

    The checkpoint package can require platform-specific libpq bindings, so
    import and initialize it only when requested.
    """
    logger.info("Checking Postgres checkpointer configuration")
    settings = get_settings()
    if not settings.enable_postgres_checkpoints:
        return None

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        return AsyncPostgresSaver.from_conn_string(settings.database_url)
    except Exception as error:
        logger.exception("Postgres checkpointing could not be initialized")
        raise RuntimeError(
            "ENABLE_POSTGRES_CHECKPOINTS is true, but the Postgres checkpointer "
            "could not be initialized"
        ) from error
