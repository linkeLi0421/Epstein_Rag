"""SQLAlchemy models for query logs, indexing jobs, and system metrics."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import config


class Base(DeclarativeBase):
    pass


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text)
    sources = Column(JSONB)  # [{"source": "file.pdf", "page": 5, "similarity": 0.89}]
    response_time_ms = Column(Integer)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    client_type = Column(String(50), index=True)  # "claude", "cursor", "dashboard", "api"
    session_id = Column(String(100))


class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50))  # "github", "upload", "local"
    source_url = Column(Text)
    status = Column(String(50), default="pending")  # "pending", "processing", "completed", "failed"
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    current_file = Column(Text)
    progress_percent = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    metadata_ = Column("metadata", JSONB)


class SystemMetrics(Base):
    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    metric_name = Column(String(100), index=True)
    metric_value = Column(Float)
    labels = Column(JSONB)


# Async engine and session factory

engine = create_async_engine(config.database_url, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
