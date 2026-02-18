# Epstein RAG System - MCP + Dashboard Architecture

## Core Concept

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MCP SERVER (Core Engine)                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Handles: Document Indexing │ RAG Queries │ LLM Generation │ Citations  │   │
│  │  Protocol: Model Context Protocol (stdio/SSE)                           │   │
│  │  Clients: Claude Desktop │ Cursor │ VS Code │ Other MCP Clients          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   DASHBOARD WEB UI   │  │   MCP CLIENTS        │  │   API CONSUMERS      │
│   (Observability)    │  │   (AI Assistants)    │  │   (Other Apps)       │
│                      │  │                      │  │                      │
│  ┌────────────────┐  │  │  ┌────────────────┐  │  │  ┌────────────────┐  │
│  │ Query Monitor  │  │  │  │ Claude Desktop │  │  │  │ Custom Apps    │  │
│  │ - History      │  │  │  │ - Chat with    │  │  │  │ - Scripts      │  │
│  │ - Stats        │  │  │  │   documents    │  │  │  │ - Integrations │  │
│  │ - Analytics    │  │  │  └────────────────┘  │  │  └────────────────┘  │
│  └────────────────┘  │  │                      │  │                      │
│                      │  │  ┌────────────────┐  │  └──────────────────────┘
│  ┌────────────────┐  │  │  │ Cursor         │  │
│  │ Data Pipeline  │  │  │  │ - Code editor  │  │
│  │ - Progress     │  │  │  │   integration  │  │
│  │ - Status       │  │  │  └────────────────┘  │
│  │ - Logs         │  │  │                      │
│  └────────────────┘  │  └──────────────────────┘
│                      │
│  ┌────────────────┐  │
│  │ System Health  │  │
│  │ - Metrics      │  │
│  │ - Performance  │  │
│  │ - Alerts       │  │
│  └────────────────┘  │
└──────────────────────┘
```

## Design Philosophy

**MCP Server = Core Engine**
- All RAG logic lives in the MCP Server
- Document processing, embedding, retrieval, generation
- Exposed via MCP Protocol (Tools/Resources)
- Can be used by any MCP-compatible client

**Dashboard = Observability Layer**
- Read-only (mostly) view into the MCP Server
- Monitor what's happening, not control it
- Query history, processing status, system metrics
- Real-time updates via WebSocket

**Why this separation?**
- MCP Server can run headless (no UI needed)
- Dashboard is optional (can disable)
- Multiple UIs can connect to same MCP Server
- Clear separation of concerns

---

## Architecture Details

### 1. MCP Server (The Brain)

```python
# mcp_server.py - Core RAG Engine

@mcp.tool()
async def index_documents(folder_path: str) -> str:
    """Index documents - can be called by any MCP client"""
    # ... indexing logic
    # Log to database for dashboard
    await log_indexing_job(job_id, status, progress)

@mcp.tool()
async def query_documents(query: str) -> str:
    """RAG query - can be called by any MCP client"""
    # ... query logic
    # Log query for dashboard
    await log_query(query, sources, response_time)
    return answer

@mcp.resource("stats://queries")
async def get_query_stats() -> str:
    """Expose query statistics"""
    return json.dumps(stats)
```

**Responsibilities:**
- Document ingestion & processing
- Vector embedding & storage
- RAG retrieval & generation
- Expose Tools/Resources via MCP
- Log all operations for observability

### 2. Dashboard Backend (The Monitor)

```python
# dashboard_backend.py - Observability API

from fastapi import FastAPI
from sqlalchemy import create_engine

app = FastAPI()

# Query Monitoring
@app.get("/api/dashboard/queries")
async def get_recent_queries(limit: int = 50):
    """Get recent queries for dashboard"""
    return db.query(QueryLog).order_by(desc(QueryLog.timestamp)).limit(limit).all()

@app.get("/api/dashboard/queries/stats")
async def get_query_statistics(time_range: str = "24h"):
    """Get query analytics"""
    return {
        "total_queries": 1234,
        "avg_response_time": 1.2,
        "top_queries": [...],
        "query_trend": [...]
    }

# Data Pipeline Monitoring
@app.get("/api/dashboard/jobs")
async def get_indexing_jobs():
    """Get document indexing jobs"""
    return db.query(IndexingJob).all()

@app.get("/api/dashboard/jobs/{job_id}/progress")
async def get_job_progress(job_id: str):
    """Get real-time job progress"""
    return {
        "job_id": job_id,
        "status": "processing",
        "progress": 65,
        "total_files": 1000,
        "processed_files": 650,
        "current_file": "document_651.pdf",
        "estimated_time_remaining": "5m 30s"
    }

# System Health
@app.get("/api/dashboard/health")
async def get_system_health():
    """Get system health metrics"""
    return {
        "status": "healthy",
        "components": {
            "mcp_server": "running",
            "vector_db": "connected",
            "llm": "available",
            "embedding": "ready"
        },
        "metrics": {
            "cpu_usage": 45,
            "memory_usage": 6.2,
            "disk_usage": 120
        }
    }

# WebSocket for real-time updates
@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """Real-time updates for dashboard"""
    await websocket.accept()
    while True:
        # Send updates every second
        await websocket.send_json({
            "type": "query_update",
            "data": get_latest_queries()
        })
        await asyncio.sleep(1)
```

**Responsibilities:**
- Query logging & analytics
- Job progress tracking
- System metrics collection
- Real-time WebSocket updates
- Read-only access to MCP operations

### 3. Dashboard Frontend (The View)

```
Dashboard UI Layout:
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏠 Dashboard    📊 Analytics    🔍 Queries    📁 Jobs    ⚙️ Settings        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │   Total Queries     │  │   Avg Response      │  │   Documents         │ │
│  │   12,456            │  │   1.2s              │  │   1,234             │ │
│  │   ↑ 23%             │  │   ↓ 0.3s            │  │   ↑ 56 today        │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │   Query Activity (Real-time)        │  │   Recent Queries            │  │
│  │                                     │  │                             │  │
│  │   📈 [Live Graph]                   │  │   • "flight logs" - 2s ago  │  │
│  │                                     │  │   • "palm beach" - 5s ago   │  │
│  │   Queries/min: 45                   │  │   • "witness list" - 1m ago │  │
│  │                                     │  │                             │  │
│  └─────────────────────────────────────┘  └─────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   Active Jobs                                                        │   │
│  │                                                                      │   │
│  │   📁 Indexing: Epstein-Files    [████████████░░░░░░░░] 65%          │   │
│  │   650/1000 files    ETA: 5m 30s    Status: Processing               │   │
│  │   Current: flight_logs_vol2.pdf                                      │   │
│  │                                                                      │   │
│  │   [Pause]  [Cancel]  [View Logs]                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │   System Health                     │  │   Top Queries               │  │
│  │                                     │  │                             │  │
│  │   ✅ MCP Server: Running            │  │   1. flight logs (234)      │  │
│  │   ✅ Vector DB: Connected           │  │   2. palm beach (189)       │  │
│  │   ✅ LLM: Available                 │  │   3. witness names (156)    │  │
│  │   ⚠️  Disk: 85% full                │  │                             │  │
│  │                                     │  │                             │  │
│  └─────────────────────────────────────┘  └─────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pages:**

1. **Dashboard (Home)**
   - Key metrics cards
   - Live query activity graph
   - Active jobs progress
   - System health status
   - Recent queries list

2. **Analytics**
   - Query trends over time
   - Popular queries
   - Response time distribution
   - Document type breakdown
   - Usage patterns

3. **Queries**
   - Full query history
   - Search/filter queries
   - View query details + sources
   - Export query logs

4. **Jobs**
   - All indexing jobs
   - Real-time progress
   - Job logs
   - Retry/cancel controls

5. **Settings**
   - MCP Server config view
   - Dashboard preferences
   - Data retention settings

---

## Data Flow

### Query Flow with Logging

```
User Query (via MCP Client)
    │
    ▼
┌─────────────────┐
│  MCP Server     │
│  query_documents│
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│  RAG Pipeline   │  │  Log to DB      │
│  - Retrieve     │  │  - Query text   │
│  - Generate     │  │  - Sources      │
│  - Return       │  │  - Timestamp    │
└────────┬────────┘  │  - Duration     │
         │           └─────────────────┘
         ▼
Response to User
         │
         ▼
Dashboard WebSocket
notifies all connected
UIs of new query
```

### Indexing Flow with Progress

```
Start Indexing Job
    │
    ▼
┌─────────────────┐
│  MCP Server     │
│  index_documents│
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│  Process Files  │  │  Update Progress│
│  - Download     │  │  - Job ID       │
│  - Chunk        │  │  - Progress %   │
│  - Embed        │  │  - Current file │
│  - Store        │  │  - ETA          │
└────────┬────────┘  └─────────────────┘
         │
         ▼
Dashboard shows
real-time progress
```

---

## Database Schema

### Query Logs
```sql
CREATE TABLE query_logs (
    id UUID PRIMARY KEY,
    query_text TEXT NOT NULL,
    response_text TEXT,
    sources JSONB,  -- [{"source": "file.pdf", "page": 5, "similarity": 0.89}]
    response_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT NOW(),
    client_type VARCHAR(50),  -- "claude", "cursor", "dashboard", "api"
    session_id VARCHAR(100)
);

CREATE INDEX idx_query_logs_timestamp ON query_logs(timestamp);
CREATE INDEX idx_query_logs_client ON query_logs(client_type);
```

### Indexing Jobs
```sql
CREATE TABLE indexing_jobs (
    id UUID PRIMARY KEY,
    source_type VARCHAR(50),  -- "github", "upload", "local"
    source_url TEXT,
    status VARCHAR(50),  -- "pending", "processing", "completed", "failed"
    total_files INTEGER,
    processed_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,
    current_file TEXT,
    progress_percent INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);
```

### System Metrics
```sql
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    metric_name VARCHAR(100),
    metric_value FLOAT,
    labels JSONB
);
```

---

## Implementation Plan

### Phase 1: MCP Server with Logging
- Add logging to all MCP tools
- Create database models
- Store query logs, job progress

### Phase 2: Dashboard Backend
- FastAPI for dashboard API
- Query analytics endpoints
- Job progress endpoints
- WebSocket for real-time updates

### Phase 3: Dashboard Frontend
- React app with dashboard UI
- Real-time charts and graphs
- Job progress visualization
- Query history browser

### Phase 4: Integration
- Connect dashboard to MCP Server logs
- Real-time sync via WebSocket
- Polish UI/UX

---

## API Endpoints Summary

### MCP Server (MCP Protocol)
```
Tools:
- index_documents(folder_path)
- query_documents(query)
- search_similar(query)
- get_document_summary(source)
- list_indexed_documents()
- delete_document(source)
- reset_index()
- check_status()

Resources:
- stats://queries
- stats://documents
- stats://system
```

### Dashboard Backend (REST API)
```
GET  /api/dashboard/queries              # Recent queries
GET  /api/dashboard/queries/stats        # Query analytics
GET  /api/dashboard/queries/{id}         # Query details

GET  /api/dashboard/jobs                 # All jobs
GET  /api/dashboard/jobs/{id}            # Job details
GET  /api/dashboard/jobs/{id}/progress   # Job progress
POST /api/dashboard/jobs/{id}/cancel     # Cancel job

GET  /api/dashboard/health               # System health
GET  /api/dashboard/metrics              # System metrics
GET  /api/dashboard/analytics            # Full analytics

WS   /ws/dashboard                       # Real-time updates
```

---

## Key Benefits

1. **Separation of Concerns**
   - MCP Server: Pure RAG logic
   - Dashboard: Pure observability
   - Can use one without the other

2. **Flexibility**
   - MCP Server can run headless
   - Dashboard is optional add-on
   - Multiple dashboards can connect

3. **Observability**
   - Full visibility into operations
   - Query history and analytics
   - Real-time job monitoring

4. **User Experience**
   - AI assistants use MCP
   - Humans use Dashboard
   - Both see the same data

---

**This architecture gives you the best of both worlds: MCP for AI integration, Dashboard for human oversight.**
