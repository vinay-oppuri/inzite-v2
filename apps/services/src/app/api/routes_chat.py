from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.app.worker import get_research_run, get_retrieved_docs
from src.core.schemas import Citation, SourceDocument

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    run_id: str
    question: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


@router.post("", response_model=ChatResponse)
async def answer_follow_up(payload: ChatRequest) -> ChatResponse:
    logger.info("Answering follow-up chat for run %s", payload.run_id)
    run = get_research_run(payload.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="research run not found")
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="research run is not completed")

    docs = get_retrieved_docs(payload.run_id)
    relevant_docs = _rank_docs(payload.question, docs)[:3]
    if not relevant_docs:
        return ChatResponse(
            answer="I don't have enough indexed context to answer that from this run.",
            citations=[],
        )

    citations = [
        Citation(doc_id=doc.doc_id, quote_or_paraphrase=_truncate(doc.content, 180))
        for doc in relevant_docs
    ]
    answer = (
        "Based on the retrieved run context, the strongest relevant evidence is: "
        + " ".join(f"{doc.title} [{doc.doc_id}]." for doc in relevant_docs)
    )
    return ChatResponse(answer=answer, citations=citations)


def _rank_docs(question: str, docs: list[SourceDocument]) -> list[SourceDocument]:
    logger.debug("Ranking %s docs for follow-up chat", len(docs))
    question_terms = set(_tokenize(question))
    if not question_terms:
        return []

    scored = []
    for doc in docs:
        doc_terms = set(_tokenize(f"{doc.title} {doc.content}"))
        score = len(question_terms & doc_terms)
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _score, doc in scored]


def _tokenize(value: str) -> list[str]:
    logger.debug("Tokenizing chat text")
    return re.findall(r"[a-zA-Z0-9]+", value.lower())


def _truncate(value: str, max_chars: int) -> str:
    logger.debug("Truncating chat citation")
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."
