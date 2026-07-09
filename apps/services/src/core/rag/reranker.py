from __future__ import annotations

import logging
import re

from src.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


def rerank_documents(query: str, docs: list[SourceDocument]) -> list[SourceDocument]:
    """Rank documents by query/document term overlap."""
    logger.info("Reranking documents")
    query_terms = set(_tokenize(query))
    if not query_terms:
        return docs

    return sorted(
        docs,
        key=lambda doc: (_overlap_score(query_terms, doc), len(doc.content)),
        reverse=True,
    )


def _overlap_score(query_terms: set[str], doc: SourceDocument) -> int:
    logger.debug("Scoring document overlap")
    doc_terms = set(_tokenize(f"{doc.title} {doc.content}"))
    return len(query_terms & doc_terms)


def _tokenize(value: str) -> list[str]:
    logger.debug("Tokenizing reranker text")
    return re.findall(r"[a-zA-Z0-9]+", value.lower())
