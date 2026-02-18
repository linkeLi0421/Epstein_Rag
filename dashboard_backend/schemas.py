"""Pydantic response models for the dashboard API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Query Models ---

class SourceInfo(BaseModel):
    source: str
    page: int | None = None
    similarity: float | None = None


class QueryLogResponse(BaseModel):
    id: UUID
    query_text: str
    response_text: str | None = None
    sources: list[dict] | None = None
    response_time_ms: int | None = None
    timestamp: datetime | None = None
    client_type: str | None = None
    session_id: str | None = None

    model_config = {"from_attributes": True}


class QueryListResponse(BaseModel):
    queries: list[QueryLogResponse]
    total: int
    page: int
    page_size: int


class QueryTrendPoint(BaseModel):
    timestamp: str
    count: int


class PopularQuery(BaseModel):
    query_text: str
    count: int


class ResponseTimeBucket(BaseModel):
    bucket: str
    count: int
    percentage: float


class QueryStatsResponse(BaseModel):
    total_queries: int
    avg_response_time_ms: float | None
    median_response_time_ms: float | None
    p95_response_time_ms: float | None
    query_trend: list[QueryTrendPoint]
    popular_queries: list[PopularQuery]
    response_time_distribution: list[ResponseTimeBucket]


# --- Job Models ---

class IndexingJobResponse(BaseModel):
    id: UUID
    source_type: str | None = None
    source_url: str | None = None
    status: str | None = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    current_file: str | None = None
    progress_percent: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    metadata: dict | None = Field(None, alias="metadata_")

    model_config = {"from_attributes": True, "populate_by_name": True}


class JobListResponse(BaseModel):
    jobs: list[IndexingJobResponse]
    total: int


class JobProgressResponse(BaseModel):
    job_id: UUID
    status: str
    progress_percent: int
    total_files: int
    processed_files: int
    failed_files: int
    current_file: str | None = None
    estimated_time_remaining: str | None = None


# --- Health Models ---

class ComponentHealth(BaseModel):
    name: str
    status: str  # "running", "connected", "available", "error", "warning"
    details: str | None = None


class SystemHealthResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: float | None = None
    components: list[ComponentHealth]


class MetricPoint(BaseModel):
    metric_name: str
    metric_value: float
    timestamp: datetime | None = None
    labels: dict | None = None


class MetricsResponse(BaseModel):
    cpu_usage: float | None = None
    memory_usage_mb: float | None = None
    disk_usage_gb: float | None = None
    active_connections: int = 0
    recent_metrics: list[MetricPoint]


# --- Analytics Models ---

class HourlyHeatmapPoint(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    hour: int  # 0-23
    count: int


class DocumentTypeBreakdown(BaseModel):
    doc_type: str
    count: int
    percentage: float


class AnalyticsResponse(BaseModel):
    total_queries: int
    total_documents: int
    total_jobs: int
    avg_response_time_ms: float | None
    query_trend: list[QueryTrendPoint]
    popular_queries: list[PopularQuery]
    response_time_distribution: list[ResponseTimeBucket]
    hourly_heatmap: list[HourlyHeatmapPoint]
    document_type_breakdown: list[DocumentTypeBreakdown]


# --- WebSocket Models ---

class WebSocketMessage(BaseModel):
    type: str  # "query_update", "job_update", "metric_update", "heartbeat"
    data: dict
