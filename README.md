# Epstein RAG System

A Retrieval-Augmented Generation (RAG) system for the Epstein document archive, built with a **Model Context Protocol (MCP) Server** as the core engine and a **real-time observability dashboard** for monitoring.

```
                      +-----------------------+
                      |     MCP SERVER        |
                      |  (Core RAG Engine)    |
                      |  - Document Indexing  |
                      |  - RAG Queries        |
                      |  - Logging            |
                      +----------+------------+
                                 |
              +------------------+------------------+
              |                  |                  |
    +---------v------+  +-------v--------+  +------v---------+
    | Dashboard      |  | MCP Clients    |  | API Consumers  |
    | (Observability)|  | Claude Desktop |  | Scripts, Apps  |
    | React Web UI   |  | Cursor, VSCode |  |                |
    +----------------+  +----------------+  +----------------+
```

## Components

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| **MCP Server** | Python, MCP SDK | 8080 | Core RAG engine - indexing, queries, retrieval |
| **Dashboard Backend** | FastAPI, SQLAlchemy | 8001 | Observability REST API + WebSocket |
| **Dashboard Frontend** | React, Tailwind, Recharts | 3000 | Real-time monitoring web UI |
| **PostgreSQL** | PostgreSQL 15 | 5432 | Query logs, job tracking, metrics |
| **ChromaDB** | ChromaDB | 8000 | Vector store for document embeddings |

## Prerequisites

- **Docker** and **Docker Compose** (v2+)
- **Python 3.11+** (for local development)
- **Node.js 20+** (for frontend development)

## Quick Start

### 1. Clone and configure

```bash
git clone <repository-url>
cd epstein_rag
cp .env.example .env
```

### 2. Start all services

```bash
docker compose up -d
```

### 3. Access the system

| Service | URL |
|---------|-----|
| Dashboard UI | http://localhost:3000 |
| Dashboard API | http://localhost:8001 |
| API Health Check | http://localhost:8001/api/dashboard/health |
| ChromaDB | http://localhost:8000 |

## MCP Tools

The MCP server exposes 8 tools for AI assistants:

| Tool | Description |
|------|-------------|
| `index_documents(folder_path)` | Index documents from a folder |
| `query_documents(query, top_k)` | RAG query with citations |
| `search_similar(query, top_k)` | Semantic similarity search |
| `get_document_summary(source)` | Get summary of a specific document |
| `list_indexed_documents()` | List all indexed documents |
| `delete_document(source)` | Remove a document from the index |
| `reset_index()` | Clear the entire vector store |
| `check_status()` | System health check |

### Claude Desktop Configuration

Add to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "epstein-rag": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/epstein_rag"
    }
  }
}
```

## Dashboard Pages

1. **Dashboard (Home)** - Key metrics, live activity, active jobs, system health
2. **Analytics** - Query trends, popular queries, response time distribution
3. **Queries** - Full query history with search/filter
4. **Jobs** - Indexing jobs with real-time progress
5. **Settings** - Configuration view and preferences

## Development

### Run tests

```bash
pip install pytest pytest-asyncio pytest-cov aiosqlite
pytest tests/ -v
```

### Run with coverage

```bash
pytest tests/ --cov=mcp_server --cov=dashboard_backend --cov=services --cov-report=term-missing
```

### Local development (without Docker)

```bash
# Backend
cd dashboard_backend && pip install -r requirements.txt
uvicorn dashboard_backend.main:app --reload --port 8001

# Frontend
cd dashboard_frontend && npm install && npm run dev

# MCP Server
cd mcp_server && pip install -r requirements.txt
python -m mcp_server
```

## Project Structure

```
epstein_rag/
|-- mcp_server/              # MCP Server - Core RAG engine
|   |-- __init__.py
|   |-- config.py            # Environment-based configuration
|   |-- models.py            # SQLAlchemy models (QueryLog, IndexingJob, etc.)
|   |-- Dockerfile
|   +-- requirements.txt
|-- dashboard_backend/       # Dashboard API (FastAPI)
|   |-- api/                 # REST endpoint routers
|   |-- config.py            # Pydantic settings
|   |-- db.py                # Database connection
|   |-- models.py            # Shared models
|   |-- Dockerfile
|   +-- requirements.txt
|-- dashboard_frontend/      # Dashboard UI (React + Vite)
|   |-- src/
|   |-- Dockerfile
|   +-- package.json
|-- services/                # Data pipeline services
|-- tests/                   # Test suite
|   |-- conftest.py          # Shared fixtures
|   |-- test_mcp_server.py
|   |-- test_dashboard_api.py
|   +-- test_data_pipeline.py
|-- docs/                    # Documentation
|-- docker-compose.yml       # Full stack orchestration
|-- .env.example             # Environment template
|-- .github/workflows/       # CI/CD
+-- pyproject.toml           # Python project config + pytest settings
```

## License

This project is for educational and research purposes.
