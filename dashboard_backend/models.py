"""SQLAlchemy models shared with the MCP server.

Imports directly from the MCP server when available to ensure schema
consistency. Falls back to local definitions if the MCP server package
is not installed (e.g. during isolated testing).
"""

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
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


try:
    from mcp_server.models import QueryLog, IndexingJob, SystemMetrics, Base  # noqa: F811

    # Alias for consistent naming in dashboard code
    SystemMetric = SystemMetrics
except ImportError:
    class QueryLog(Base):
        __tablename__ = "query_logs"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        query_text = Column(Text, nullable=False)
        response_text = Column(Text)
        sources = Column(JSONB)
        response_time_ms = Column(Integer)
        timestamp = Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            index=True,
        )
        client_type = Column(String(50), index=True)
        session_id = Column(String(100))

    class IndexingJob(Base):
        __tablename__ = "indexing_jobs"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        source_type = Column(String(50))
        source_url = Column(Text)
        status = Column(String(50), default="pending")
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

    # Alias for consistent naming
    SystemMetric = SystemMetrics
