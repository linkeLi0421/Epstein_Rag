"""Job monitoring endpoints for the dashboard."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from dashboard_backend.db import get_db
from dashboard_backend.models import IndexingJob
from dashboard_backend.schemas import (
    IndexingJobResponse,
    JobListResponse,
    JobProgressResponse,
)

router = APIRouter(prefix="/api/dashboard/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def get_indexing_jobs(
    status: str | None = Query(default=None, description="Filter by status: pending, processing, completed, failed"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get all indexing jobs with optional status filter."""
    query = select(IndexingJob)

    if status:
        query = query.where(IndexingJob.status == status)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results, active jobs first then by start time
    query = query.order_by(
        desc(IndexingJob.status == "processing"),
        desc(IndexingJob.started_at),
    ).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    return JobListResponse(
        jobs=[IndexingJobResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/{job_id}", response_model=IndexingJobResponse)
async def get_job_detail(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific indexing job."""
    result = await db.execute(select(IndexingJob).where(IndexingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return IndexingJobResponse.model_validate(job)


@router.get("/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get real-time progress for a specific indexing job."""
    result = await db.execute(select(IndexingJob).where(IndexingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Estimate time remaining based on processing rate
    eta = None
    if job.status == "processing" and job.processed_files and job.started_at:
        from datetime import datetime, timezone
        elapsed = (datetime.now(timezone.utc) - job.started_at.replace(tzinfo=timezone.utc)).total_seconds()
        if job.processed_files > 0 and elapsed > 0:
            rate = job.processed_files / elapsed
            remaining_files = (job.total_files or 0) - job.processed_files
            if rate > 0:
                remaining_seconds = remaining_files / rate
                minutes = int(remaining_seconds // 60)
                seconds = int(remaining_seconds % 60)
                eta = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    return JobProgressResponse(
        job_id=job.id,
        status=job.status or "unknown",
        progress_percent=job.progress_percent or 0,
        total_files=job.total_files or 0,
        processed_files=job.processed_files or 0,
        failed_files=job.failed_files or 0,
        current_file=job.current_file,
        estimated_time_remaining=eta,
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Request cancellation of an indexing job."""
    result = await db.execute(select(IndexingJob).where(IndexingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("pending", "processing"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status}'. Only pending or processing jobs can be cancelled.",
        )

    job.status = "cancelled"
    job.error_message = "Cancelled by user via dashboard"
    await db.commit()

    # Broadcast cancellation via websocket
    from dashboard_backend.api.websocket import broadcast
    await broadcast({
        "type": "job_update",
        "data": {
            "job_id": str(job.id),
            "status": "cancelled",
            "message": "Job cancelled by user",
        },
    })

    return {"message": "Job cancellation requested", "job_id": str(job_id)}
