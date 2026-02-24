"""Health, metrics, and analytics endpoints for the dashboard."""

import time

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, desc, extract, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from dashboard_backend.config import get_settings
from dashboard_backend.db import get_db
from dashboard_backend.models import IndexingJob, QueryLog, SystemMetric
from dashboard_backend.schemas import (
    AnalyticsResponse,
    ComponentHealth,
    DocumentTypeBreakdown,
    HourlyHeatmapPoint,
    MetricPoint,
    MetricsResponse,
    PopularQuery,
    QueryTrendPoint,
    ResponseTimeBucket,
    SystemHealthResponse,
)

router = APIRouter(prefix="/api/dashboard", tags=["health"])

# Track server start time for uptime
_start_time = time.time()


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
):
    """Get system health status for all components."""
    components = []

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        components.append(ComponentHealth(name="PostgreSQL", status="connected"))
    except Exception as e:
        components.append(ComponentHealth(name="PostgreSQL", status="error", details=str(e)))

    # Check MCP server (look for recent metrics or queries)
    try:
        recent_query = await db.execute(
            select(QueryLog.timestamp)
            .order_by(desc(QueryLog.timestamp))
            .limit(1)
        )
        last_query = recent_query.scalar_one_or_none()
        if last_query:
            components.append(ComponentHealth(name="MCP Server", status="running", details=f"Last query: {last_query}"))
        else:
            components.append(ComponentHealth(name="MCP Server", status="running", details="No queries yet"))
    except Exception:
        components.append(ComponentHealth(name="MCP Server", status="unknown", details="Could not determine status"))

    # Check for active indexing jobs
    active_jobs_result = await db.execute(
        select(func.count()).select_from(IndexingJob).where(IndexingJob.status == "processing")
    )
    active_count = active_jobs_result.scalar() or 0
    components.append(
        ComponentHealth(
            name="Indexing Engine",
            status="running" if active_count > 0 else "idle",
            details=f"{active_count} active job(s)",
        )
    )

    # Check vector DB by probing ChromaDB directly
    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=5.0) as client:
            vdb_resp = await client.get(
                f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/tenants/default_tenant/databases/default_database/collections/{settings.chroma_collection}"
            )
            if vdb_resp.status_code == 200:
                count_resp = await client.get(
                    f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/tenants/default_tenant/databases/default_database/collections/{vdb_resp.json()['id']}/count"
                )
                doc_count = count_resp.json() if count_resp.status_code == 200 else "?"
                components.append(ComponentHealth(name="Vector Database", status="connected", details=f"{doc_count} chunks indexed"))
            else:
                components.append(ComponentHealth(name="Vector Database", status="warning", details="Collection not found"))
    except Exception:
        components.append(ComponentHealth(name="Vector Database", status="error", details="ChromaDB unreachable"))

    # Determine overall status
    statuses = [c.status for c in components]
    if "error" in statuses:
        overall = "unhealthy"
    elif "unknown" in statuses or "warning" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return SystemHealthResponse(
        status=overall,
        uptime_seconds=round(time.time() - _start_time, 1),
        components=components,
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_system_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Get current system metrics."""
    # Fetch the latest metrics from the database
    latest_metrics_query = (
        select(SystemMetric)
        .order_by(desc(SystemMetric.timestamp))
        .limit(50)
    )
    result = await db.execute(latest_metrics_query)
    metrics = result.scalars().all()

    # Extract specific metrics from the latest batch
    cpu = None
    memory = None
    disk = None
    for m in metrics:
        if m.metric_name == "cpu_usage" and cpu is None:
            cpu = m.metric_value
        elif m.metric_name == "memory_usage_mb" and memory is None:
            memory = m.metric_value
        elif m.metric_name == "disk_usage_gb" and disk is None:
            disk = m.metric_value

    # Active DB connections (approximate)
    conn_result = await db.execute(text(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
    ))
    active_connections = conn_result.scalar() or 0

    return MetricsResponse(
        cpu_usage=cpu,
        memory_usage_mb=memory,
        disk_usage_gb=disk,
        active_connections=active_connections,
        recent_metrics=[
            MetricPoint(
                metric_name=m.metric_name,
                metric_value=m.metric_value,
                timestamp=m.timestamp,
                labels=m.labels,
            )
            for m in metrics
        ],
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    time_range: str = Query(default="24h", description="e.g. 1h, 24h, 7d, 30d"),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive analytics data for the dashboard."""
    interval = _parse_time_range(time_range) or "24 hours"
    since = func.now() - text(f"interval '{interval}'")

    # Total queries
    total_queries_result = await db.execute(
        select(func.count()).select_from(QueryLog).where(QueryLog.timestamp >= since)
    )
    total_queries = total_queries_result.scalar() or 0

    # Average response time
    avg_time_result = await db.execute(
        select(func.avg(QueryLog.response_time_ms)).where(QueryLog.timestamp >= since)
    )
    avg_response_time = avg_time_result.scalar()

    # Total documents indexed (sum of processed_files from completed jobs)
    total_docs_result = await db.execute(
        select(func.sum(IndexingJob.processed_files)).where(IndexingJob.status == "completed")
    )
    total_documents = total_docs_result.scalar() or 0

    # Total jobs
    total_jobs_result = await db.execute(select(func.count()).select_from(IndexingJob))
    total_jobs = total_jobs_result.scalar() or 0

    # Query trend (hourly buckets)
    trend_query = (
        select(
            func.date_trunc("hour", QueryLog.timestamp).label("bucket"),
            func.count(QueryLog.id).label("count"),
        )
        .where(QueryLog.timestamp >= since)
        .group_by(text("bucket"))
        .order_by(text("bucket"))
    )
    trend_result = await db.execute(trend_query)
    query_trend = [
        QueryTrendPoint(timestamp=str(row.bucket), count=row.count)
        for row in trend_result.all()
    ]

    # Popular queries
    popular_query = (
        select(QueryLog.query_text, func.count(QueryLog.id).label("count"))
        .where(QueryLog.timestamp >= since)
        .group_by(QueryLog.query_text)
        .order_by(desc("count"))
        .limit(10)
    )
    popular_result = await db.execute(popular_query)
    popular_queries = [
        PopularQuery(query_text=row.query_text, count=row.count)
        for row in popular_result.all()
    ]

    # Response time distribution
    total_for_pct = max(total_queries, 1)
    buckets_query = select(
        func.sum(case((QueryLog.response_time_ms < 500, 1), else_=0)).label("under_500"),
        func.sum(case((QueryLog.response_time_ms.between(500, 999), 1), else_=0)).label("b500_1000"),
        func.sum(case((QueryLog.response_time_ms.between(1000, 1999), 1), else_=0)).label("b1000_2000"),
        func.sum(case((QueryLog.response_time_ms.between(2000, 4999), 1), else_=0)).label("b2000_5000"),
        func.sum(case((QueryLog.response_time_ms >= 5000, 1), else_=0)).label("over_5000"),
    ).where(QueryLog.timestamp >= since)
    buckets_result = await db.execute(buckets_query)
    b = buckets_result.one()
    response_time_distribution = [
        ResponseTimeBucket(bucket="<0.5s", count=b.under_500 or 0, percentage=round((b.under_500 or 0) / total_for_pct * 100, 1)),
        ResponseTimeBucket(bucket="0.5-1s", count=b.b500_1000 or 0, percentage=round((b.b500_1000 or 0) / total_for_pct * 100, 1)),
        ResponseTimeBucket(bucket="1-2s", count=b.b1000_2000 or 0, percentage=round((b.b1000_2000 or 0) / total_for_pct * 100, 1)),
        ResponseTimeBucket(bucket="2-5s", count=b.b2000_5000 or 0, percentage=round((b.b2000_5000 or 0) / total_for_pct * 100, 1)),
        ResponseTimeBucket(bucket=">5s", count=b.over_5000 or 0, percentage=round((b.over_5000 or 0) / total_for_pct * 100, 1)),
    ]

    # Hourly heatmap (day of week x hour of day)
    heatmap_query = (
        select(
            extract("dow", QueryLog.timestamp).label("dow"),
            extract("hour", QueryLog.timestamp).label("hour"),
            func.count(QueryLog.id).label("count"),
        )
        .where(QueryLog.timestamp >= since)
        .group_by(text("dow"), text("hour"))
        .order_by(text("dow"), text("hour"))
    )
    heatmap_result = await db.execute(heatmap_query)
    hourly_heatmap = [
        HourlyHeatmapPoint(
            day_of_week=int(row.dow),
            hour=int(row.hour),
            count=row.count,
        )
        for row in heatmap_result.all()
    ]

    # Document type breakdown from indexing job metadata
    doc_type_query = (
        select(
            IndexingJob.source_type,
            func.count(IndexingJob.id).label("count"),
        )
        .group_by(IndexingJob.source_type)
        .order_by(desc("count"))
    )
    doc_type_result = await db.execute(doc_type_query)
    doc_types_raw = doc_type_result.all()
    total_type_count = sum(r.count for r in doc_types_raw) or 1
    document_type_breakdown = [
        DocumentTypeBreakdown(
            doc_type=row.source_type or "unknown",
            count=row.count,
            percentage=round(row.count / total_type_count * 100, 1),
        )
        for row in doc_types_raw
    ]

    return AnalyticsResponse(
        total_queries=total_queries,
        total_documents=total_documents,
        total_jobs=total_jobs,
        avg_response_time_ms=round(avg_response_time, 1) if avg_response_time else None,
        query_trend=query_trend,
        popular_queries=popular_queries,
        response_time_distribution=response_time_distribution,
        hourly_heatmap=hourly_heatmap,
        document_type_breakdown=document_type_breakdown,
    )


def _parse_time_range(time_range: str) -> str | None:
    mapping = {
        "1h": "1 hour",
        "6h": "6 hours",
        "12h": "12 hours",
        "24h": "24 hours",
        "7d": "7 days",
        "30d": "30 days",
        "90d": "90 days",
    }
    return mapping.get(time_range)
