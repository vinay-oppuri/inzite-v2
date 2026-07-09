from __future__ import annotations

import logging

from src.app.config import get_settings
from src.core.rag.embeddings import embed_texts
from src.core.rag.qdrant_store import (
    collection_name_for_run,
    ensure_collection,
    upsert_documents,
)
from src.core.schemas import GraphState, SourceDocument

logger = logging.getLogger(__name__)


async def rag_index_node(state: GraphState) -> dict:
    """Index retrieved documents in Qdrant when vector indexing is configured."""
    settings = get_settings()

    logger.info("Running RAG Index")
    if not should_index(state):
        logger.info("Skipping RAG Index")
        return {}

    documents, vectors, errors = await embed_documents(state.retrieved_docs)
    if not documents:
        return {"error_log": [*state.error_log, *errors]}

    try:
        collection_name = collection_name_for_run(state.run_id)
        logger.info("Upserting %s documents to Qdrant collection %s", len(documents), collection_name)
        await ensure_collection(
            settings.qdrant_url,
            collection_name,
            len(vectors[0]),
            api_key=settings.qdrant_api_key,
        )
        await upsert_documents(
            qdrant_url=settings.qdrant_url,
            collection_name=collection_name,
            run_id=state.run_id,
            documents=documents,
            vectors=vectors,
            api_key=settings.qdrant_api_key,
        )
    except Exception as error:
        logger.exception("RAG index upsert failed")
        errors.append(f"rag_index qdrant upsert failed: {error}")

    return {"error_log": [*state.error_log, *errors]}


def should_index(state: GraphState) -> bool:
    logger.debug("Checking whether RAG indexing should run")
    settings = get_settings()
    return bool(
        state.retrieved_docs
        and settings.enable_rag_indexing
        and not settings.disable_live_calls
    )


async def embed_documents(
    documents: list[SourceDocument],
) -> tuple[list[SourceDocument], list[list[float]], list[str]]:
    logger.info("Embedding %s retrieved documents", len(documents))
    indexed_documents: list[SourceDocument] = []
    vectors: list[list[float]] = []
    errors: list[str] = []

    for document in documents:
        try:
            vector = (await embed_texts([document.content]))[0]
        except Exception as error:
            errors.append(f"rag_index skipped {document.doc_id}: {error}")
            continue

        indexed_documents.append(document)
        vectors.append(vector)

    return indexed_documents, vectors, errors
