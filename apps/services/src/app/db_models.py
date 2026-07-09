from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    logger.debug("Generating database UUID")
    return str(uuid.uuid4())


def _now() -> datetime:
    logger.debug("Generating database timestamp")
    return datetime.now(timezone.utc)


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    idea_raw: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_log_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    report: Mapped[Report | None] = relationship(back_populates="research_run")
    chat_sessions: Mapped[list[ChatSession]] = relationship(back_populates="research_run")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    research_run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), unique=True)
    markdown: Mapped[str] = mapped_column(Text)
    strategy_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    research_run: Mapped[ResearchRun] = relationship(back_populates="report")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    research_run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), index=True)
    messages_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    research_run: Mapped[ResearchRun] = relationship(back_populates="chat_sessions")
