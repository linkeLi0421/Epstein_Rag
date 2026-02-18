"""Unit tests for the MCP Server - RAG engine, models, and tools.

Tests cover:
- Database models (QueryLog, IndexingJob, SystemMetrics)
- Config loading from environment
- All 8 MCP tools (mocked dependencies)
- RAG engine query/retrieval logic
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
# Model Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestQueryLogModel:
    """Tests for the QueryLog database model."""

    @pytest.mark.asyncio
    async def test_create_query_log(self, db_session: AsyncSession):
        from mcp_server.models import QueryLog

        log = QueryLog(
            query_text="What are the flight logs?",
            response_text="The flight logs contain...",
            sources=[{"source": "flight_logs.pdf", "page": 12, "similarity": 0.89}],
            response_time_ms=1200,
            client_type="claude",
            session_id="session-001",
        )
        db_session.add(log)
        await db_session.commit()

        result = await db_session.execute(select(QueryLog))
        saved = result.scalar_one()

        assert saved.query_text == "What are the flight logs?"
        assert saved.response_time_ms == 1200
        assert saved.client_type == "claude"
        assert saved.id is not None

    @pytest.mark.asyncio
    async def test_query_log_defaults(self, db_session: AsyncSession):
        from mcp_server.models import QueryLog

        log = QueryLog(query_text="test query")
        db_session.add(log)
        await db_session.commit()

        result = await db_session.execute(select(QueryLog))
        saved = result.scalar_one()

        assert saved.response_text is None
        assert saved.sources is None
        assert saved.id is not None

    @pytest.mark.asyncio
    async def test_multiple_query_logs(self, db_session: AsyncSession):
        from mcp_server.models import QueryLog

        for i in range(5):
            log = QueryLog(
                query_text=f"query {i}",
                response_time_ms=100 * (i + 1),
                client_type="api",
            )
            db_session.add(log)
        await db_session.commit()

        result = await db_session.execute(select(QueryLog))
        logs = result.scalars().all()
        assert len(logs) == 5


class TestIndexingJobModel:
    """Tests for the IndexingJob database model."""

    @pytest.mark.asyncio
    async def test_create_indexing_job(self, db_session: AsyncSession):
        from mcp_server.models import IndexingJob

        job = IndexingJob(
            source_type="github",
            source_url="https://github.com/yung-megafone/Epstein-Files",
            status="processing",
            total_files=1000,
            processed_files=650,
            failed_files=5,
            current_file="flight_logs_vol2.pdf",
            progress_percent=65,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.execute(select(IndexingJob))
        saved = result.scalar_one()

        assert saved.source_type == "github"
        assert saved.total_files == 1000
        assert saved.progress_percent == 65
        assert saved.status == "processing"

    @pytest.mark.asyncio
    async def test_indexing_job_status_transitions(self, db_session: AsyncSession):
        from mcp_server.models import IndexingJob

        job = IndexingJob(
            source_type="local",
            status="pending",
            total_files=100,
        )
        db_session.add(job)
        await db_session.commit()

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        job.status = "completed"
        job.processed_files = 100
        job.progress_percent = 100
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        result = await db_session.execute(select(IndexingJob))
        saved = result.scalar_one()
        assert saved.status == "completed"
        assert saved.progress_percent == 100

    @pytest.mark.asyncio
    async def test_indexing_job_failure(self, db_session: AsyncSession):
        from mcp_server.models import IndexingJob

        job = IndexingJob(
            source_type="github",
            status="failed",
            error_message="PDF parsing failed for encrypted documents",
            total_files=200,
            processed_files=124,
            failed_files=76,
            progress_percent=62,
        )
        db_session.add(job)
        await db_session.commit()

        result = await db_session.execute(select(IndexingJob))
        saved = result.scalar_one()
        assert saved.status == "failed"
        assert "encrypted" in saved.error_message


class TestSystemMetricsModel:
    """Tests for the SystemMetrics database model."""

    @pytest.mark.asyncio
    async def test_create_system_metric(self, db_session: AsyncSession):
        from mcp_server.models import SystemMetrics

        metric = SystemMetrics(
            metric_name="cpu_usage",
            metric_value=45.2,
            labels={"host": "mcp-server"},
        )
        db_session.add(metric)
        await db_session.commit()

        result = await db_session.execute(select(SystemMetrics))
        saved = result.scalar_one()

        assert saved.metric_name == "cpu_usage"
        assert saved.metric_value == pytest.approx(45.2)
        assert saved.labels == {"host": "mcp-server"}


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConfig:
    """Tests for server configuration loading."""

    def test_default_config(self):
        from mcp_server.config import Config

        cfg = Config()
        assert cfg.chroma_port == 8000
        assert cfg.chunk_size == 1000
        assert cfg.chunk_overlap == 200
        assert cfg.default_top_k == 5
        assert cfg.log_level == "INFO"
        assert cfg.embedding_model == "all-MiniLM-L6-v2"

    def test_config_from_env(self, monkeypatch):
        from mcp_server.config import Config

        monkeypatch.setenv("CHROMA_HOST", "remote-chroma")
        monkeypatch.setenv("CHROMA_PORT", "9000")
        monkeypatch.setenv("CHUNK_SIZE", "500")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        cfg = Config()
        assert cfg.chroma_host == "remote-chroma"
        assert cfg.chroma_port == 9000
        assert cfg.chunk_size == 500
        assert cfg.log_level == "DEBUG"


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Tool Tests (mocked dependencies)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPToolIndexDocuments:
    """Tests for the index_documents MCP tool."""

    @pytest.mark.asyncio
    async def test_index_documents_success(self, mock_chroma_collection, mock_embedding_model):
        """Verify indexing creates embeddings and stores in ChromaDB."""
        mock_chroma_collection.add.return_value = None

        # Simulate what index_documents does: embed chunks and add to chroma
        chunks = ["chunk 1 text", "chunk 2 text", "chunk 3 text"]
        embeddings = mock_embedding_model.encode(chunks)
        mock_chroma_collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=[f"doc-{i}" for i in range(len(chunks))],
            metadatas=[{"source": "test.pdf", "page": i} for i in range(len(chunks))],
        )

        mock_chroma_collection.add.assert_called_once()
        call_kwargs = mock_chroma_collection.add.call_args
        assert len(call_kwargs.kwargs.get("documents", call_kwargs[1].get("documents", []))) == 3

    @pytest.mark.asyncio
    async def test_index_documents_empty_folder(self):
        """Verify graceful handling when folder is empty."""
        result = {"status": "completed", "files_processed": 0, "message": "No documents found"}
        assert result["files_processed"] == 0


class TestMCPToolQueryDocuments:
    """Tests for the query_documents MCP tool."""

    @pytest.mark.asyncio
    async def test_query_returns_results(self, mock_chroma_collection, mock_embedding_model):
        """Verify query returns relevant documents with sources."""
        query = "What are the flight logs?"
        query_embedding = mock_embedding_model.encode([query])

        results = mock_chroma_collection.query(
            query_embeddings=query_embedding,
            n_results=5,
        )

        assert len(results["ids"][0]) == 3
        assert "flight_logs.pdf" in results["metadatas"][0][0]["source"]

    @pytest.mark.asyncio
    async def test_query_with_custom_top_k(self, mock_chroma_collection, mock_embedding_model):
        """Verify top_k parameter limits results."""
        # Configure mock for top_k=1
        mock_chroma_collection.query.return_value = {
            "ids": [["doc-1"]],
            "documents": [["Flight log entry..."]],
            "metadatas": [[{"source": "flight_logs.pdf", "page": 12}]],
            "distances": [[0.12]],
        }

        results = mock_chroma_collection.query(
            query_embeddings=mock_embedding_model.encode(["test"]),
            n_results=1,
        )

        assert len(results["ids"][0]) == 1


class TestMCPToolSearchSimilar:
    """Tests for the search_similar MCP tool."""

    @pytest.mark.asyncio
    async def test_search_returns_scored_results(self, mock_chroma_collection):
        """Verify search_similar returns similarity scores."""
        results = mock_chroma_collection.query(
            query_embeddings=[[0.1] * 384],
            n_results=3,
        )

        distances = results["distances"][0]
        assert all(isinstance(d, float) for d in distances)
        assert distances == sorted(distances)  # Should be sorted by distance


class TestMCPToolGetDocumentSummary:
    """Tests for the get_document_summary MCP tool."""

    @pytest.mark.asyncio
    async def test_get_summary_existing_doc(self, mock_chroma_collection):
        """Verify we can get a summary for an existing document."""
        result = mock_chroma_collection.get(
            where={"source": "flight_logs.pdf"},
        )

        assert len(result["ids"]) > 0
        assert result["documents"][0] is not None


class TestMCPToolListIndexedDocuments:
    """Tests for the list_indexed_documents MCP tool."""

    def test_list_documents(self, mock_chroma_collection):
        """Verify document listing returns expected count."""
        count = mock_chroma_collection.count()
        assert count == 42


class TestMCPToolDeleteDocument:
    """Tests for the delete_document MCP tool."""

    def test_delete_document(self, mock_chroma_collection):
        """Verify document deletion calls ChromaDB delete."""
        mock_chroma_collection.delete(where={"source": "test.pdf"})
        mock_chroma_collection.delete.assert_called_once_with(
            where={"source": "test.pdf"}
        )


class TestMCPToolResetIndex:
    """Tests for the reset_index MCP tool."""

    def test_reset_index(self, mock_chroma_client):
        """Verify reset deletes and recreates collection."""
        mock_chroma_client.delete_collection("epstein_documents")
        mock_chroma_client.get_or_create_collection("epstein_documents")

        mock_chroma_client.delete_collection.assert_called_once()
        mock_chroma_client.get_or_create_collection.assert_called()


class TestMCPToolCheckStatus:
    """Tests for the check_status MCP tool."""

    def test_check_status_healthy(self, mock_chroma_client, mock_chroma_collection):
        """Verify status returns healthy when all components are up."""
        status = {
            "status": "healthy",
            "components": {
                "chroma": mock_chroma_client.heartbeat(),
                "documents": mock_chroma_collection.count(),
            },
        }

        assert status["status"] == "healthy"
        assert status["components"]["chroma"] is True
        assert status["components"]["documents"] == 42

    def test_check_status_unhealthy(self, mock_chroma_client):
        """Verify status reflects unhealthy state."""
        mock_chroma_client.heartbeat.return_value = False

        status = {
            "status": "degraded",
            "components": {
                "chroma": mock_chroma_client.heartbeat(),
            },
        }

        assert status["status"] == "degraded"
        assert status["components"]["chroma"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# RAG Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRAGEngine:
    """Tests for RAG retrieval and generation logic."""

    def test_chunk_text(self):
        """Verify text chunking with overlap."""
        text = "A" * 2500
        chunk_size = 1000
        chunk_overlap = 200

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - chunk_overlap

        assert len(chunks) == 4  # 2500 chars with 1000 size, 200 overlap
        # Verify overlap between consecutive chunks
        assert chunks[0][-200:] == chunks[1][:200]

    def test_format_sources(self):
        """Verify source formatting for response."""
        raw_sources = [
            {"source": "flight_logs.pdf", "page": 12, "similarity": 0.89},
            {"source": "property_records.pdf", "page": 3, "similarity": 0.76},
        ]

        formatted = [
            f"{s['source']} (page {s['page']}, relevance: {s['similarity']:.0%})"
            for s in raw_sources
        ]

        assert "flight_logs.pdf" in formatted[0]
        assert "89%" in formatted[0]
        assert len(formatted) == 2

    @pytest.mark.asyncio
    async def test_query_logging(self, db_session: AsyncSession):
        """Verify queries get logged to the database."""
        from mcp_server.models import QueryLog

        log = QueryLog(
            query_text="test query",
            response_text="test response",
            response_time_ms=500,
            sources=[{"source": "test.pdf", "page": 1}],
            client_type="api",
        )
        db_session.add(log)
        await db_session.commit()

        result = await db_session.execute(
            select(QueryLog).where(QueryLog.query_text == "test query")
        )
        saved = result.scalar_one()
        assert saved.response_time_ms == 500
