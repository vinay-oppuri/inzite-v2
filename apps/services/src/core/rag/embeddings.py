from __future__ import annotations

import hashlib
import logging
import math

from src.app.config import get_settings

logger = logging.getLogger(__name__)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Create deterministic local vectors for optional Qdrant indexing."""

    logger.info("Creating local embeddings for %s texts", len(texts))
    settings = get_settings()
    if settings.embedding_provider != "local":
        raise ValueError(
            "Groq does not expose a text embeddings endpoint. "
            "Set EMBEDDING_PROVIDER=local or add another embedding provider."
        )

    return [
        embed_text(text, dimensions=settings.embedding_dimensions)
        for text in texts
    ]


def embed_text(text: str, dimensions: int) -> list[float]:
    logger.debug("Embedding one text locally")
    if dimensions <= 0:
        raise ValueError("EMBEDDING_DIMENSIONS must be greater than zero")

    vector = [0.0] * dimensions
    tokens = text.lower().split()

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    magnitude = math.sqrt(sum(value * value for value in vector))
    if not magnitude:
        return vector

    return [value / magnitude for value in vector]


__all__ = ["embed_texts"]
