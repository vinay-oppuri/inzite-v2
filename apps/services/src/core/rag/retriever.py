from __future__ import annotations

import logging
import re

from rank_bm25 import BM25Okapi

from src.core.schemas import SourceDocument, StartupIntent

logger = logging.getLogger(__name__)


def retrieve_relevant_docs(
    intent: StartupIntent,
    docs: list[SourceDocument],
    limit: int = 8,
) -> list[SourceDocument]:
    """Local BM25 retrieval over the current run's SourceDocuments."""
    logger.info("Retrieving relevant documents")
    if not docs:
        return []

    query = _intent_query(intent)
    tokenized_docs = [_tokenize(f"{doc.title} {doc.content}") for doc in docs]
    if not any(tokenized_docs):
        return docs[:limit]

    bm25 = BM25Okapi(tokenized_docs)
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(
        zip(docs, scores, strict=True),
        key=lambda item: (_agent_boost(item[0].agent), float(item[1])),
        reverse=True,
    )
    return [doc for doc, _score in ranked[:limit]]


def _intent_query(intent: StartupIntent) -> str:
    logger.debug("Building retrieval query from intent")
    return " ".join(
        part
        for part in (
            intent.idea_raw,
            intent.industry,
            intent.target_audience,
            intent.problem_statement,
            intent.proposed_solution,
            " ".join(intent.data_needs),
        )
        if part
    )


def _agent_boost(agent: str) -> float:
    logger.debug("Applying retrieval boost for %s agent", agent)
    return {"competitor": 0.3, "trend": 0.2, "paper": 0.1}.get(agent, 0.0)


def _tokenize(value: str) -> list[str]:
    logger.debug("Tokenizing retrieval text")
    return re.findall(r"[a-zA-Z0-9]+", value.lower())
