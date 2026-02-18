"""Query log endpoints for the dashboard."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, text, case, literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from dashboard_backend.db import get_db
from dashboard_backend.models import QueryLog
from dashboard_backend.schemas import (
    PopularQuery,
    QueryListResponse,
    QueryLogResponse,
    QueryStatsResponse,
    QueryTrendPoint,
    ResponseTimeBucket,
)

router = APIRouter(prefix="/api/dashboard/queries", tags=["queries"])


@router.get("", response_model=QueryListResponse)
async def get_recent_queries(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    client_type: str | None = Query(default=None),
    time_range: str | None = Query(default=None, description="e.g. 1h, 24h, 7d, 30d"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent queries with optional filtering."""
    query = select(QueryLog)

    if search:
        query = query.where(QueryLog.query_text.ilike(f"%{search}%"))
    if client_type:
        query = query.where(QueryLog.client_type == client_type)
    if time_range:
        interval = _parse_time_range(time_range)
        if interval:
            query = query.where(QueryLog.timestamp >= func.now() - text(f"interval '{interval}'"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(QueryLog.timestamp)).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    return QueryListResponse(
        queries=[QueryLogResponse.model_validate(r) for r in rows],
        total=total,
        page=offset // limit + 1,
        page_size=limit,
    )


@router.get("/stats", response_model=QueryStatsResponse)
async def get_query_statistics(
    time_range: str = Query(default="24h", description="e.g. 1h, 24h, 7d, 30d"),
    db: AsyncSession = Depends(get_db),
):
    """Get query statistics and analytics for the given time range."""
    interval = _parse_time_range(time_range) or "24 hours"
    since = func.now() - text(f"interval '{interval}'")

    # Basic stats
    stats_query = select(
        func.count(QueryLog.id).label("total"),
        func.avg(QueryLog.response_time_ms).label("avg_time"),
        func.percentile_cont(0.5).within_group(QueryLog.response_time_ms).label("median_time"),
        func.percentile_cont(0.95).within_group(QueryLog.response_time_ms).label("p95_time"),
    ).where(QueryLog.timestamp >= since)
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.one()

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
    trend = [
        QueryTrendPoint(timestamp=str(row.bucket), count=row.count)
        for row in trend_result.all()
    ]

    # Popular queries
    popular_query = (
        select(
            QueryLog.query_text,
            func.count(QueryLog.id).label("count"),
        )
        .where(QueryLog.timestamp >= since)
        .group_by(QueryLog.query_text)
        .order_by(desc("count"))
        .limit(10)
    )
    popular_result = await db.execute(popular_query)
    popular = [
        PopularQuery(query_text=row.query_text, count=row.count)
        for row in popular_result.all()
    ]

    # Response time distribution
    total_count = stats_row.total or 1
    buckets_query = select(
        func.sum(case((QueryLog.response_time_ms < 500, 1), else_=0)).label("under_500"),
        func.sum(case((QueryLog.response_time_ms.between(500, 999), 1), else_=0)).label("500_1000"),
        func.sum(case((QueryLog.response_time_ms.between(1000, 1999), 1), else_=0)).label("1000_2000"),
        func.sum(case((QueryLog.response_time_ms.between(2000, 4999), 1), else_=0)).label("2000_5000"),
        func.sum(case((QueryLog.response_time_ms >= 5000, 1), else_=0)).label("over_5000"),
    ).where(QueryLog.timestamp >= since)
    buckets_result = await db.execute(buckets_query)
    b = buckets_result.one()

    distribution = [
        ResponseTimeBucket(bucket="<0.5s", count=b.under_500 or 0, percentage=round((b.under_500 or 0) / total_count * 100, 1)),
        ResponseTimeBucket(bucket="0.5-1s", count=b[1] or 0, percentage=round((b[1] or 0) / total_count * 100, 1)),
        ResponseTimeBucket(bucket="1-2s", count=b[2] or 0, percentage=round((b[2] or 0) / total_count * 100, 1)),
        ResponseTimeBucket(bucket="2-5s", count=b[3] or 0, percentage=round((b[3] or 0) / total_count * 100, 1)),
        ResponseTimeBucket(bucket=">5s", count=b[4] or 0, percentage=round((b[4] or 0) / total_count * 100, 1)),
    ]

    return QueryStatsResponse(
        total_queries=stats_row.total or 0,
        avg_response_time_ms=round(stats_row.avg_time, 1) if stats_row.avg_time else None,
        median_response_time_ms=round(stats_row.median_time, 1) if stats_row.median_time else None,
        p95_response_time_ms=round(stats_row.p95_time, 1) if stats_row.p95_time else None,
        query_trend=trend,
        popular_queries=popular,
        response_time_distribution=distribution,
    )


@router.get("/{query_id}", response_model=QueryLogResponse)
async def get_query_detail(
    query_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific query by ID."""
    result = await db.execute(select(QueryLog).where(QueryLog.id == query_id))
    query_log = result.scalar_one_or_none()
    if not query_log:
        raise HTTPException(status_code=404, detail="Query not found")
    return QueryLogResponse.model_validate(query_log)


def _parse_time_range(time_range: str) -> str | None:
    """Convert shorthand time range to PostgreSQL interval string."""
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
