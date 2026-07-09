import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    disable_live_calls: bool = False
    artifact_root: str = "data/memory_store"
    raw_docs_root: str = "data/raw_docs"
    enforce_internal_api_key: bool = False
    internal_api_key: str = ""

    # Groq
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3-32b"

    # RAG indexing
    enable_rag_indexing: bool = False
    embedding_provider: str = "local"
    embedding_dimensions: int = 384

    # Research APIs
    tavily_api_key: str = ""
    news_api_key: str = ""
    semantic_scholar_api_key: str = ""

    enable_keyless_live_sources: bool = False

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres"
        "@localhost:5432/research_agent"
    )

    enable_postgres_checkpoints: bool = False

    # Vector Database
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Cache
    redis_url: str = "redis://localhost:6379/0"

    # Observability
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


@lru_cache
def get_settings() -> Settings:
    """Return the application settings."""

    logger.debug("Loading application settings")
    return Settings()
