# Yeh file SQLite ke saare database models define karti hai.
# SQLAlchemy ORM use hua hai — har table ek class hai.
# Interview sessions, agent runs, aur results yahan store hote hain.

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from backend.utils.config import get_settings

settings = get_settings()


# --- Enums ---

class AgentStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ESCALATED = "escalated"


class InterviewStatus(str, PyEnum):
    CREATED = "created"
    ANALYZING = "analyzing"
    QUESTIONS_READY = "questions_ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# --- Base ---

class Base(DeclarativeBase):
    pass


# --- Models ---

class InterviewSession(Base):
    """Ek complete interview session — CV upload se final report tak."""

    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status: Mapped[InterviewStatus] = mapped_column(Enum(InterviewStatus), default=InterviewStatus.CREATED)

    cv_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jd_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cv_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analysis_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    questions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    agent_runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="session", cascade="all, delete-orphan")
    interview_answers: Mapped[list["InterviewAnswer"]] = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")


class AgentRun(Base):
    """Har agent execution ka record — retry history ke saath."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.PENDING)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    critique: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="agent_runs")


class InterviewAnswer(Base):
    """Voice interview mein har sawal ka jawab aur score."""

    __tablename__ = "interview_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="interview_answers")


# --- DB setup helpers ---

def get_engine():
    """SQLAlchemy engine banao settings se."""
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=settings.debug,
    )


def get_session_factory():
    """Session factory — FastAPI dependency injection ke liye."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Pehli baar run karo — saari tables ban jaayengi."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
