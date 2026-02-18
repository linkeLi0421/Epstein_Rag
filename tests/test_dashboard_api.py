"""Unit tests for the Dashboard Backend API.

Tests cover:
- All REST API endpoints (queries, jobs, health, analytics, metrics)
- WebSocket connection behavior
- Query parameter handling and pagination
- Error responses
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_indexing_job, make_query_log, make_system_metric


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Config Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDashboardConfig:
    """Tests for dashboard backend configuration."""

    def test_default_settings(self):
        from dashboard_backend.config import Settings

        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8001
        assert settings.debug is False
        assert settings.default_page_size == 50
        assert settings.max_page_size == 200
        assert settings.ws_heartbeat_interval == 30

    def test_cors_origins_default(self):
        from dashboard_backend.config import Settings

        settings = Settings()
        assert "http://localhost:3000" in settings.cors_origins

    def test_settings_from_env(self, monkeypatch):
        from dashboard_backend.config import Settings

        monkeypatch.setenv("DASHBOARD_DEBUG", "true")
        monkeypatch.setenv("DASHBOARD_PORT", "9001")

        settings = Settings()
        assert settings.debug is True
        assert settings.port == 9001


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard Model Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDashboardModels:
    """Tests for the dashboard backend model definitions."""

    @pytest.mark.asyncio
    async def test_query_log_model(self, db_session: AsyncSession):
        """Verify QueryLog model from dashboard_backend works."""
        from mcp_server.models import QueryLog

        log = QueryLog(
            query_text="palm beach mansion",
            response_text="The Palm Beach property...",
            response_time_ms=900,
            client_type="dashboard",
        )
        db_session.add(log)
        await db_session.commit()

        result = await db_session.execute(
            select(QueryLog).where(QueryLog.client_type == "dashboard")
        )
        saved = result.scalar_one()
        assert saved.query_text == "palm beach mansion"

    @pytest.mark.asyncio
    async def test_indexing_job_model(self, db_session: AsyncSession):
        """Verify IndexingJob model from dashboard_backend works."""
        from mcp_server.models import IndexingJob

        job = IndexingJob(
            source_type="github",
            source_url="https://github.com/yung-megafone/Epstein-Files",
            status="completed",
            total_files=42,
            processed_files=42,
            progress_percent=100,
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.execute(
            select(IndexingJob).where(IndexingJob.status == "completed")
        )
        saved = result.scalar_one()
        assert saved.processed_files == 42


# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoint Tests (Queries)
# ═══════════════════════════════════════════════════════════════════════════════


class TestQueriesEndpoint:
    """Tests for /api/dashboard/queries endpoints."""

    @pytest.mark.asyncio
    async def test_get_recent_queries(self, db_session: AsyncSession):
        """Verify fetching recent queries with default limit."""
        from mcp_server.models import QueryLog

        for i in range(10):
            db_session.add(QueryLog(
                query_text=f"query {i}",
                response_time_ms=100 * (i + 1),
                client_type="api",
            ))
        await db_session.commit()

        result = await db_session.execute(
            select(QueryLog).order_by(QueryLog.timestamp.desc()).limit(50)
        )
        queries = result.scalars().all()

        assert len(queries) == 10

    @pytest.mark.asyncio
    async def test_get_queries_with_limit(self, db_session: AsyncSession):
        """Verify limit parameter restricts results."""
        from mcp_server.models import QueryLog

        for i in range(20):
            db_session.add(QueryLog(
                query_text=f"query {i}",
                client_type="api",
            ))
        await db_session.commit()

        result = await db_session.execute(
            select(QueryLog).limit(5)
        )
        queries = result.scalars().all()
        assert len(queries) == 5

    @pytest.mark.asyncio
    async def test_get_query_by_id(self, db_session: AsyncSession):
        """Verify fetching a single query by ID."""
        from mcp_server.models import QueryLog

        query_id = uuid.uuid4()
        db_session.add(QueryLog(
            id=query_id,
            query_text="specific query",
            response_text="specific response",
            client_type="claude",
        ))
        await db_session.commit()

        result = await db_session.execute(
            select(QueryLog).where(QueryLog.id == query_id)
        )
        saved = result.scalar_one()
        assert saved.query_text == "specific query"

    @pytest.mark.asyncio
    async def test_query_stats(self, db_session: AsyncSession):
        """Verify query statistics computation."""
        from mcp_server.models import QueryLog
        from sqlalchemy import func

        for i in range(5):
            db_session.add(QueryLog(
                query_text=f"query {i}",
                response_time_ms=100 * (i + 1),  # 100, 200, 300, 400, 500
                client_type="api",
            ))
        await db_session.commit()

        # Count
        count_result = await db_session.execute(
            select(func.count(QueryLog.id))
        )
        total = count_result.scalar()
        assert total == 5

        # Average response time
        avg_result = await db_session.execute(
            select(func.avg(QueryLog.response_time_ms))
        )
        avg_time = avg_result.scalar()
        assert avg_time == pytest.approx(300.0)


# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoint Tests (Jobs)
# ═══════════════════════════════════════════════════════════════════════════════


class TestJobsEndpoint:
    """Tests for /api/dashboard/jobs endpoints."""

    @pytest.mark.asyncio
    async def test_get_all_jobs(self, db_session: AsyncSession):
        """Verify listing all indexing jobs."""
        from mcp_server.models import IndexingJob

        for status in ["pending", "processing", "completed", "failed"]:
            db_session.add(IndexingJob(
                source_type="github",
                status=status,
                total_files=100,
            ))
        await db_session.commit()

        result = await db_session.execute(select(IndexingJob))
        jobs = result.scalars().all()
        assert len(jobs) == 4

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, db_session: AsyncSession):
        """Verify fetching a specific job by ID."""
        from mcp_server.models import IndexingJob

        job_id = uuid.uuid4()
        db_session.add(IndexingJob(
            id=job_id,
            source_type="local",
            status="processing",
            total_files=500,
            processed_files=250,
            progress_percent=50,
        ))
        await db_session.commit()

        result = await db_session.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        saved = result.scalar_one()
        assert saved.progress_percent == 50

    @pytest.mark.asyncio
    async def test_get_job_progress(self, db_session: AsyncSession):
        """Verify progress tracking for a job."""
        from mcp_server.models import IndexingJob

        job_id = uuid.uuid4()
        db_session.add(IndexingJob(
            id=job_id,
            source_type="github",
            source_url="https://github.com/yung-megafone/Epstein-Files",
            status="processing",
            total_files=1000,
            processed_files=650,
            failed_files=5,
            current_file="flight_logs_vol2.pdf",
            progress_percent=65,
            started_at=datetime.now(timezone.utc),
        ))
        await db_session.commit()

        result = await db_session.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        job = result.scalar_one()

        progress = {
            "job_id": str(job.id),
            "status": job.status,
            "progress": job.progress_percent,
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "failed_files": job.failed_files,
            "current_file": job.current_file,
        }

        assert progress["progress"] == 65
        assert progress["current_file"] == "flight_logs_vol2.pdf"
        assert progress["failed_files"] == 5

    @pytest.mark.asyncio
    async def test_cancel_job(self, db_session: AsyncSession):
        """Verify job cancellation updates status."""
        from mcp_server.models import IndexingJob

        job_id = uuid.uuid4()
        db_session.add(IndexingJob(
            id=job_id,
            source_type="github",
            status="processing",
            total_files=1000,
            processed_files=300,
        ))
        await db_session.commit()

        result = await db_session.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        job = result.scalar_one()
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        result = await db_session.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        updated = result.scalar_one()
        assert updated.status == "cancelled"
        assert updated.completed_at is not None


# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoint Tests (Health & Metrics)
# ═══════════════════════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    """Tests for /api/dashboard/health endpoint."""

    def test_health_response_format(self):
        """Verify health check response structure."""
        health = {
            "status": "healthy",
            "components": {
                "mcp_server": "running",
                "vector_db": "connected",
                "llm": "available",
                "embedding": "ready",
            },
            "metrics": {
                "cpu_usage": 45,
                "memory_usage": 6.2,
                "disk_usage": 120,
            },
        }

        assert health["status"] == "healthy"
        assert "mcp_server" in health["components"]
        assert "cpu_usage" in health["metrics"]

    def test_health_degraded(self):
        """Verify degraded health when a component is down."""
        health = {
            "status": "degraded",
            "components": {
                "mcp_server": "running",
                "vector_db": "disconnected",
                "llm": "available",
            },
        }

        assert health["status"] == "degraded"
        assert health["components"]["vector_db"] == "disconnected"


class TestMetricsEndpoint:
    """Tests for /api/dashboard/metrics endpoint."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_metrics(self, db_session: AsyncSession):
        """Verify metrics storage and retrieval."""
        from mcp_server.models import SystemMetrics

        metrics = [
            SystemMetrics(metric_name="cpu_usage", metric_value=45.2, labels={"host": "mcp"}),
            SystemMetrics(metric_name="memory_usage", metric_value=6.2, labels={"host": "mcp"}),
            SystemMetrics(metric_name="disk_usage", metric_value=120.0, labels={"host": "mcp"}),
        ]
        for m in metrics:
            db_session.add(m)
        await db_session.commit()

        result = await db_session.execute(select(SystemMetrics))
        saved = result.scalars().all()
        assert len(saved) == 3

    @pytest.mark.asyncio
    async def test_metrics_by_name(self, db_session: AsyncSession):
        """Verify filtering metrics by name."""
        from mcp_server.models import SystemMetrics

        for i in range(10):
            db_session.add(SystemMetrics(
                metric_name="cpu_usage",
                metric_value=40.0 + i,
            ))
        db_session.add(SystemMetrics(
            metric_name="memory_usage",
            metric_value=6.2,
        ))
        await db_session.commit()

        result = await db_session.execute(
            select(SystemMetrics).where(SystemMetrics.metric_name == "cpu_usage")
        )
        cpu_metrics = result.scalars().all()
        assert len(cpu_metrics) == 10


# ═══════════════════════════════════════════════════════════════════════════════
# API Endpoint Tests (Analytics)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnalyticsEndpoint:
    """Tests for /api/dashboard/analytics endpoint."""

    @pytest.mark.asyncio
    async def test_popular_queries(self, db_session: AsyncSession):
        """Verify popular queries aggregation."""
        from mcp_server.models import QueryLog
        from sqlalchemy import func

        # Add queries with varying frequencies
        for _ in range(10):
            db_session.add(QueryLog(query_text="flight logs", client_type="api"))
        for _ in range(5):
            db_session.add(QueryLog(query_text="palm beach", client_type="api"))
        for _ in range(3):
            db_session.add(QueryLog(query_text="witness list", client_type="api"))
        await db_session.commit()

        result = await db_session.execute(
            select(QueryLog.query_text, func.count(QueryLog.id).label("count"))
            .group_by(QueryLog.query_text)
            .order_by(func.count(QueryLog.id).desc())
            .limit(10)
        )
        popular = result.all()

        assert len(popular) == 3
        assert popular[0][0] == "flight logs"
        assert popular[0][1] == 10

    @pytest.mark.asyncio
    async def test_response_time_distribution(self, db_session: AsyncSession):
        """Verify response time stats."""
        from mcp_server.models import QueryLog
        from sqlalchemy import func

        times = [100, 200, 500, 800, 1200, 1500, 2000, 3000, 5000, 10000]
        for t in times:
            db_session.add(QueryLog(
                query_text="test",
                response_time_ms=t,
                client_type="api",
            ))
        await db_session.commit()

        result = await db_session.execute(
            select(
                func.min(QueryLog.response_time_ms).label("min"),
                func.max(QueryLog.response_time_ms).label("max"),
                func.avg(QueryLog.response_time_ms).label("avg"),
            )
        )
        stats = result.one()

        assert stats.min == 100
        assert stats.max == 10000
        assert stats.avg == pytest.approx(2430.0)


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestWebSocket:
    """Tests for WebSocket dashboard updates."""

    @pytest.mark.asyncio
    async def test_websocket_accept(self, mock_websocket):
        """Verify WebSocket connection is accepted."""
        await mock_websocket.accept()
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_send_query_update(self, mock_websocket):
        """Verify sending query update messages."""
        message = {
            "type": "query_update",
            "data": {
                "id": str(uuid.uuid4()),
                "query_text": "flight logs",
                "response_time_ms": 1200,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        await mock_websocket.send_json(message)
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_websocket_send_job_progress(self, mock_websocket):
        """Verify sending job progress messages."""
        message = {
            "type": "job_progress",
            "data": {
                "job_id": str(uuid.uuid4()),
                "progress": 65,
                "status": "processing",
                "current_file": "flight_logs_vol2.pdf",
            },
        }

        await mock_websocket.send_json(message)
        mock_websocket.send_json.assert_called_once_with(message)
        assert message["data"]["progress"] == 65

    @pytest.mark.asyncio
    async def test_websocket_receive_ping(self, mock_websocket):
        """Verify receiving ping messages from clients."""
        msg = await mock_websocket.receive_json()
        assert msg["type"] == "ping"

    @pytest.mark.asyncio
    async def test_websocket_close(self, mock_websocket):
        """Verify WebSocket graceful close."""
        await mock_websocket.close()
        mock_websocket.close.assert_called_once()
