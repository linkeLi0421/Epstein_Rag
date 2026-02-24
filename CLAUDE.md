# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Epstein Documents RAG system with two main parts: an **MCP Server** (stdio-based, used by Claude Desktop/Cursor) and a **Dashboard** (web UI for observability). All services share a single PostgreSQL database.

## Common Commands

### Docker (primary way to run)
```bash
cp .env.example .env
docker compose up -d                          # Start all services
docker compose up -d --build dashboard-frontend  # Rebuild + restart one service
docker compose build --no-cache dashboard-frontend  # Force full rebuild
docker compose logs <service> --tail 40       # View logs
docker compose down                           # Stop everything
```

### Python tests
```bash
pip install pytest pytest-asyncio pytest-cov aiosqlite
pytest tests/ -v                              # Run all tests
pytest tests/test_mcp_server.py -v            # Single test file
pytest tests/ --cov=mcp_server --cov=dashboard_backend --cov=services --cov-report=term-missing
```

### Linting
```bash
pip install ruff
ruff check mcp_server/ dashboard_backend/ services/ tests/
ruff format --check mcp_server/ dashboard_backend/ services/ tests/
```

### Frontend
```bash
cd dashboard_frontend
npm install
npm run dev          # Dev server on :3000 with API proxy to :8000
npm run build        # Production build (runs tsc -b && vite build)
```

### Local development (without Docker)
```bash
# Terminal 1: Backend API
uvicorn dashboard_backend.main:app --reload --port 8001

# Terminal 2: Frontend dev
cd dashboard_frontend && npm run dev

# MCP Server (launched by Claude Desktop, not manually)
python -m mcp_server
```

## Architecture

```
PostgreSQL (shared)          ChromaDB (vectors)
     ▲  ▲  ▲                     ▲  ▲
     │  │  │                     │  │
     │  │  └── services/         │  │
     │  │      (data pipeline)───┘  │
     │  │                           │
     │  └── dashboard_backend/      │
     │      (FastAPI :8001)         │
     │           ▲                  │
     │           │ /api/dashboard/* │
     │           │                  │
     │      dashboard_frontend/     │
     │      (React :3000)           │
     │                              │
     └── mcp_server/                │
         (stdio for Claude Desktop)─┘
```

**Key architectural decisions:**
- MCP Server is stdio-based (not HTTP). It's launched by MCP clients like Claude Desktop, not as a web service. The Docker container for it will restart-loop — this is expected.
- Dashboard backend is read-only against the shared database. MCP Server and services/pipeline write to it.
- services/pipeline.py operates independently — it directly connects to PostgreSQL and ChromaDB without importing mcp_server.

## Shared Database Schema

Defined in `mcp_server/models.py` (SQLAlchemy async). Three tables:
- **query_logs**: RAG queries with response text, sources (JSONB), response_time_ms, client_type
- **indexing_jobs**: Pipeline progress tracking (status, files processed, progress_percent)
- **system_metrics**: CPU/memory/disk snapshots

`dashboard_backend/models.py` imports from mcp_server.models with a fallback to local copies. If you change the schema, update mcp_server/models.py first — it's the source of truth.

## Cross-Service Gotchas

**Environment variable prefixes differ per service:**
- MCP Server: `DATABASE_URL`, `CHROMA_HOST`, `EMBEDDING_MODEL`, etc. (no prefix)
- Dashboard Backend: `DASHBOARD_DATABASE_URL`, `DASHBOARD_PORT`, etc. (`DASHBOARD_` prefix)
- Frontend: `VITE_API_URL`, `VITE_WS_URL` (build-time args, not runtime)

**API response format:** Backend wraps arrays in objects (`{"queries": [...], "total": N}`). The frontend API client in `src/lib/api.ts` unwraps these — if you add new list endpoints, follow the same pattern.

**Response time units:** Stored as milliseconds in DB (`response_time_ms`), frontend divides by 1000 for display.

**Tests use SQLite, not PostgreSQL:** `tests/conftest.py` compiles JSONB→JSON and UUID→VARCHAR for SQLite compatibility. Mock ChromaDB returns hardcoded results.

## Configuration

- `mcp_server/config.py`: Dataclass with env var defaults
- `dashboard_backend/config.py`: Pydantic BaseSettings with `DASHBOARD_` env prefix
- `.env.example`: All environment variables with defaults

## Docker Services (docker-compose.yml)

| Service | Port | Health Check |
|---------|------|-------------|
| postgres | 5432 | pg_isready |
| chromadb | 8000 | bash /dev/tcp |
| mcp-server | 8080 | N/A (stdio, will restart) |
| dashboard-backend | 8001 | python urllib |
| dashboard-frontend | 3000 | curl localhost:80 |

ChromaDB uses **v2 API** (v1 is deprecated). Health checks avoid curl inside containers that don't have it.
