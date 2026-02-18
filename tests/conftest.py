"""Shared test fixtures for the Epstein RAG system test suite.

Provides:
- In-memory SQLite database for fast tests (no Postgres required)
- Mock ChromaDB collection
- Mock MCP server context
- Pre-populated test data factories
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

# ---------------------------------------------------------------------------
# Compile-time type adapters so PostgreSQL-only types work on SQLite.
# These are registered at module import time (before any engine is created).
# ---------------------------------------------------------------------------

from sqlalchemy.dialects.postgresql import JSONB, UUID


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "VARCHAR(36)"


# ---------------------------------------------------------------------------
# Database fixtures (SQLite async via aiosqlite)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Enable foreign key support for SQLite
    @sa_event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import models and create all tables
    from mcp_server.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide a transactional database session that rolls back after each test."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Mock ChromaDB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_chroma_collection():
    """Return a mock ChromaDB collection with basic query/add support."""
    collection = MagicMock()
    collection.name = "test_documents"
    collection.count.return_value = 42

    collection.query.return_value = {
        "ids": [["doc-1", "doc-2", "doc-3"]],
        "documents": [
            [
                "Flight log entry for 2002-03-15...",
                "Property records from Palm Beach...",
                "Witness statement regarding visits...",
            ]
        ],
        "metadatas": [
            [
                {"source": "flight_logs.pdf", "page": 12},
                {"source": "property_records.pdf", "page": 3},
                {"source": "witness_statement.pdf", "page": 1},
            ]
        ],
        "distances": [[0.12, 0.25, 0.38]],
    }

    collection.add.return_value = None
    collection.delete.return_value = None
    collection.get.return_value = {
        "ids": ["doc-1"],
        "documents": ["Flight log entry..."],
        "metadatas": [{"source": "flight_logs.pdf", "page": 12}],
    }

    return collection


@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Return a mock ChromaDB client."""
    client = MagicMock()
    client.get_or_create_collection.return_value = mock_chroma_collection
    client.get_collection.return_value = mock_chroma_collection
    client.heartbeat.return_value = True
    return client


# ---------------------------------------------------------------------------
# Test data factories
# ---------------------------------------------------------------------------


def make_query_log(**overrides) -> dict:
    """Factory for QueryLog-compatible dictionaries."""
    defaults = {
        "id": uuid.uuid4(),
        "query_text": "What are the flight logs?",
        "response_text": "The flight logs show travel records...",
        "sources": [
            {"source": "flight_logs.pdf", "page": 12, "similarity": 0.89}
        ],
        "response_time_ms": 1200,
        "timestamp": datetime.now(timezone.utc),
        "client_type": "claude",
        "session_id": "test-session-001",
    }
    defaults.update(overrides)
    return defaults


def make_indexing_job(**overrides) -> dict:
    """Factory for IndexingJob-compatible dictionaries."""
    defaults = {
        "id": uuid.uuid4(),
        "source_type": "github",
        "source_url": "https://github.com/yung-megafone/Epstein-Files",
        "status": "processing",
        "total_files": 1000,
        "processed_files": 650,
        "failed_files": 5,
        "current_file": "flight_logs_vol2.pdf",
        "progress_percent": 65,
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "error_message": None,
    }
    defaults.update(overrides)
    return defaults


def make_system_metric(**overrides) -> dict:
    """Factory for SystemMetrics-compatible dictionaries."""
    defaults = {
        "id": uuid.uuid4(),
        "timestamp": datetime.now(timezone.utc),
        "metric_name": "cpu_usage",
        "metric_value": 45.2,
        "labels": {"host": "mcp-server"},
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Mock embedding model
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_embedding_model():
    """Return a mock sentence-transformer embedding model."""
    model = MagicMock()
    # Return a consistent 384-dim vector for any input
    model.encode.return_value = [[0.1] * 384]
    return model


# ---------------------------------------------------------------------------
# Mock HTTP / WebSocket helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_websocket():
    """Return a mock WebSocket connection."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock(return_value={"type": "ping"})
    ws.close = AsyncMock()
    return ws
