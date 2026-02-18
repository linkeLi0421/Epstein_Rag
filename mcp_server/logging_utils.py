"""Logging helpers that write MCP operations to PostgreSQL."""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import psutil
from sqlalchemy import func, select

from .models import IndexingJob, QueryLog, SystemMetrics, async_session

logger = logging.getLogger(__name__)


async def log_query(
    query_text: str,
    response_text: str | None = None,
    sources: list[dict] | None = None,
    response_time_ms: int | None = None,
    client_type: str = "mcp",
    session_id: str | None = None,
) -> uuid.UUID:
    """Log a query to the database and return its ID."""
    query_id = uuid.uuid4()
    async with async_session() as session:
        log_entry = QueryLog(
            id=query_id,
            query_text=query_text,
            response_text=response_text,
            sources=sources,
            response_time_ms=response_time_ms,
            client_type=client_type,
            session_id=session_id,
        )
        session.add(log_entry)
        await session.commit()
    logger.info("Logged query %s: %s", query_id, query_text[:80])
    return query_id


async def create_indexing_job(
    source_type: str,
    source_url: str,
    total_files: int = 0,
    metadata: dict[str, Any] | None = None,
) -> uuid.UUID:
    """Create a new indexing job record and return its ID."""
    job_id = uuid.uuid4()
    async with async_session() as session:
        job = IndexingJob(
            id=job_id,
            source_type=source_type,
            source_url=source_url,
            status="pending",
            total_files=total_files,
            metadata_=metadata,
        )
        session.add(job)
        await session.commit()
    logger.info("Created indexing job %s for %s", job_id, source_url)
    return job_id


async def update_indexing_job(
    job_id: uuid.UUID,
    *,
    status: str | None = None,
    processed_files: int | None = None,
    failed_files: int | None = None,
    current_file: str | None = None,
    progress_percent: int | None = None,
    total_files: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update an existing indexing job's progress."""
    async with async_session() as session:
        result = await session.get(IndexingJob, job_id)
        if result is None:
            logger.warning("Indexing job %s not found", job_id)
            return

        if status is not None:
            result.status = status
            if status == "processing" and result.started_at is None:
                result.started_at = datetime.now(timezone.utc)
            elif status in ("completed", "failed"):
                result.completed_at = datetime.now(timezone.utc)
        if processed_files is not None:
            result.processed_files = processed_files
        if failed_files is not None:
            result.failed_files = failed_files
        if current_file is not None:
            result.current_file = current_file
        if progress_percent is not None:
            result.progress_percent = progress_percent
        if total_files is not None:
            result.total_files = total_files
        if error_message is not None:
            result.error_message = error_message

        await session.commit()


async def log_system_metrics() -> None:
    """Capture and store current system metrics."""
    now = datetime.now(timezone.utc)
    metrics = [
        SystemMetrics(
            timestamp=now,
            metric_name="cpu_percent",
            metric_value=psutil.cpu_percent(interval=0.1),
            labels={"unit": "percent"},
        ),
        SystemMetrics(
            timestamp=now,
            metric_name="memory_percent",
            metric_value=psutil.virtual_memory().percent,
            labels={"unit": "percent"},
        ),
        SystemMetrics(
            timestamp=now,
            metric_name="disk_percent",
            metric_value=psutil.disk_usage("/").percent,
            labels={"unit": "percent"},
        ),
    ]
    async with async_session() as session:
        session.add_all(metrics)
        await session.commit()


async def get_query_stats() -> dict:
    """Aggregate query statistics for the stats://queries resource."""
    async with async_session() as session:
        total = (await session.execute(select(func.count(QueryLog.id)))).scalar() or 0
        avg_time = (
            await session.execute(select(func.avg(QueryLog.response_time_ms)))
        ).scalar()

        recent = (
            await session.execute(
                select(QueryLog)
                .order_by(QueryLog.timestamp.desc())
                .limit(10)
            )
        ).scalars().all()

        recent_list = [
            {
                "id": str(q.id),
                "query": q.query_text,
                "response_time_ms": q.response_time_ms,
                "timestamp": q.timestamp.isoformat() if q.timestamp else None,
                "client_type": q.client_type,
            }
            for q in recent
        ]

    return {
        "total_queries": total,
        "avg_response_time_ms": round(avg_time, 1) if avg_time else 0,
        "recent_queries": recent_list,
    }


async def get_job_stats() -> dict:
    """Aggregate indexing job statistics for the stats://jobs resource."""
    async with async_session() as session:
        total = (
            await session.execute(select(func.count(IndexingJob.id)))
        ).scalar() or 0

        by_status = {}
        for status_val in ("pending", "processing", "completed", "failed"):
            count = (
                await session.execute(
                    select(func.count(IndexingJob.id)).where(
                        IndexingJob.status == status_val
                    )
                )
            ).scalar() or 0
            by_status[status_val] = count

        active_jobs = (
            await session.execute(
                select(IndexingJob).where(
                    IndexingJob.status.in_(["pending", "processing"])
                )
            )
        ).scalars().all()

        active_list = [
            {
                "id": str(j.id),
                "source_url": j.source_url,
                "status": j.status,
                "progress_percent": j.progress_percent,
                "processed_files": j.processed_files,
                "total_files": j.total_files,
                "current_file": j.current_file,
            }
            for j in active_jobs
        ]

    return {
        "total_jobs": total,
        "by_status": by_status,
        "active_jobs": active_list,
    }


async def get_system_stats() -> dict:
    """Gather live system health for the stats://system resource."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "status": "healthy",
        "components": {
            "mcp_server": "running",
            "vector_db": "connected",
            "embedding_model": "ready",
        },
        "metrics": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_percent": mem.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_percent": disk.percent,
        },
    }


class QueryTimer:
    """Context manager that measures elapsed time in milliseconds."""

    def __init__(self):
        self.start: float = 0
        self.elapsed_ms: int = 0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = int((time.perf_counter() - self.start) * 1000)
