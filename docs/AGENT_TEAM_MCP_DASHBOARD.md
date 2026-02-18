# Claude Code Agent Team Prompt
## Epstein RAG System - MCP Server + Observability Dashboard

```
Create an agent team with 5 teammates for building an Epstein Documents 
RAG system with TWO key components:

1. MCP SERVER (Core Engine)
   - RAG functionality exposed via Model Context Protocol
   - Can be used by Claude Desktop, Cursor, VS Code, etc.
   - Logs all operations for observability

2. DASHBOARD WEB UI (Observability)
   - Monitor queries in real-time
   - Track data processing progress
   - View analytics and system health
   - Read-only view into MCP operations

Dataset: https://github.com/yung-megafone/Epstein-Files
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP SERVER (Core)                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  RAG Engine: Document Processing │ Embedding │ Retrieval │ Generation  │ │
│  │  Protocol: MCP (Tools + Resources)                                      │ │
│  │  Clients: Claude │ Cursor │ VS Code │ Any MCP-compatible client        │ │
│  │  Logging: All operations logged to database for dashboard              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  DASHBOARD BACKEND   │  │   MCP CLIENTS        │  │   API CLIENTS        │
│  (Observability API) │  │   (AI Assistants)    │  │   (Scripts/Apps)     │
│                      │  │                      │  │                      │
│  ┌────────────────┐  │  │  ┌────────────────┐  │  │  ┌────────────────┐  │
│  │ Query Logs     │  │  │  │ Claude Desktop │  │  │  │ Python scripts │  │
│  │ Job Progress   │  │  │  │ - Chat with    │  │  │  │ - Automation   │  │
│  │ Analytics      │  │  │  │   documents    │  │  │  │ - Integration  │  │
│  └────────────────┘  │  │  └────────────────┘  │  │  └────────────────┘  │
│                      │  │                      │  │                      │
└──────────┬───────────┘  └──────────────────────┘  └──────────────────────┘
           │
           ▼ WebSocket
┌──────────────────────┐
│  DASHBOARD FRONTEND  │
│  (React Web UI)      │
│                      │
│  ┌────────────────┐  │
│  │ 📊 Dashboard   │  │
│  │ 📈 Analytics   │  │
│  │ 🔍 Queries     │  │
│  │ 📁 Jobs        │  │
│  └────────────────┘  │
└──────────────────────┘
```

---

## 👥 Agent Assignments

### AGENT 1: MCP Server Engineer
**Focus**: Core RAG engine with MCP protocol + logging

**Tasks**:
1. Create/refine MCP Server with all RAG tools:
   ```python
   @mcp.tool()
   async def index_documents(folder_path: str) -> str:
       """Index documents and log progress"""
       
   @mcp.tool()
   async def query_documents(query: str) -> str:
       """RAG query and log to database"""
   ```

2. Add comprehensive logging:
   - Query logs (text, response, sources, timestamp, duration)
   - Indexing job logs (progress, status, files processed)
   - System metrics (CPU, memory, disk)

3. Create database models:
   - `QueryLog` - Store all queries
   - `IndexingJob` - Track indexing progress
   - `SystemMetrics` - Performance data

4. Expose MCP Resources for stats:
   ```python
   @mcp.resource("stats://queries")
   async def get_query_stats() -> str
   
   @mcp.resource("stats://jobs")
   async def get_job_stats() -> str
   ```

**Deliverables**:
- `mcp_server/` with complete RAG + logging
- Database models (SQLAlchemy)
- All MCP tools working
- Logs all operations

---

### AGENT 2: Dashboard Backend Engineer
**Focus**: Observability API for the dashboard

**Tasks**:
1. Create FastAPI dashboard backend:
   ```python
   # Query monitoring endpoints
   @app.get("/api/dashboard/queries")
   async def get_recent_queries(limit: int = 50)
   
   @app.get("/api/dashboard/queries/stats")
   async def get_query_statistics(time_range: str = "24h")
   
   # Job monitoring endpoints
   @app.get("/api/dashboard/jobs")
   async def get_indexing_jobs()
   
   @app.get("/api/dashboard/jobs/{id}/progress")
   async def get_job_progress(job_id: str)
   
   # System health
   @app.get("/api/dashboard/health")
   async def get_system_health()
   ```

2. Implement WebSocket for real-time updates:
   ```python
   @app.websocket("/ws/dashboard")
   async def dashboard_websocket(websocket: WebSocket)
   ```

3. Create analytics aggregations:
   - Query trends over time
   - Popular queries
   - Response time distribution
   - Document type breakdown

4. Connect to MCP Server database (read-only)

**Deliverables**:
- `dashboard_backend/` with FastAPI
- REST API endpoints
- WebSocket real-time updates
- Analytics queries

---

### AGENT 3: Dashboard Frontend Engineer
**Focus**: React web UI for observability

**Tasks**:
1. Create React app with pages:
   - **Dashboard** (Home): Key metrics, live activity, active jobs
   - **Analytics**: Charts, trends, popular queries
   - **Queries**: Full query history with search/filter
   - **Jobs**: Indexing jobs with progress bars
   - **Settings**: Configuration view

2. Build key components:
   ```tsx
   // Dashboard components
   <StatCards />           // Total queries, avg response time, documents
   <LiveActivityChart />   // Real-time query activity
   <ActiveJobsList />      // Progress bars for indexing jobs
   <RecentQueriesList />   // Latest queries with details
   <SystemHealthStatus />  // Component health indicators
   
   // Analytics components
   <QueryTrendsChart />    // Line chart of queries over time
   <PopularQueriesTable /> // Most common queries
   <ResponseTimeChart />   // Histogram of response times
   
   // Jobs components
   <JobProgressCard />     // Individual job with progress
   <JobLogsViewer />       // Real-time logs
   ```

3. Implement real-time updates:
   - WebSocket connection to backend
   - Live query activity
   - Job progress updates
   - System metrics refresh

4. Styling:
   - Tailwind CSS
   - shadcn/ui components
   - Dark mode support
   - Responsive design

**Deliverables**:
- `dashboard_frontend/` with React
- 5 pages with full functionality
- Real-time WebSocket updates
- Charts and visualizations

---

### AGENT 4: Data Pipeline Engineer
**Focus**: GitHub dataset downloader + document processing

**Tasks**:
1. Create GitHub dataset downloader:
   ```python
   class GitHubDatasetDownloader:
       async def download_repo(url: str, job_id: str)
       async def get_progress(job_id: str) -> dict
   ```

2. Build document processing pipeline:
   - PDF text extraction (PyMuPDF)
   - Text chunking with overlap
   - Metadata extraction (page numbers, doc type)
   - Batch processing with progress tracking

3. Integrate with MCP Server:
   - Call `index_documents` from downloader
   - Update job progress in database
   - Handle errors and retries

4. Optimize for large datasets:
   - Parallel processing
   - Resume capability
   - Memory-efficient streaming

**Deliverables**:
- `services/dataset_downloader.py`
- `services/document_processor.py`
- Can download & process Epstein-Files repo
- Progress tracking integrated

---

### AGENT 5: DevOps + QA Engineer
**Focus**: Docker, deployment, testing, documentation

**Tasks**:
1. Docker setup for all services:
   ```yaml
   # docker-compose.yml
   services:
     mcp-server:
       build: ./mcp_server
     dashboard-backend:
       build: ./dashboard_backend
     dashboard-frontend:
       build: ./dashboard_frontend
     postgres:
       image: postgres:15
     chromadb:
       image: chromadb/chroma
   ```

2. CI/CD pipeline:
   - GitHub Actions workflow
   - Automated testing
   - Docker image building

3. Testing:
   - MCP Server tests (pytest)
   - Dashboard backend tests
   - Dashboard frontend tests (Vitest)
   - E2E tests (Playwright)

4. Documentation:
   - `README.md` - Project overview
   - `MCP_API.md` - MCP tools reference
   - `DASHBOARD.md` - Dashboard usage
   - `DEPLOYMENT.md` - Deployment guide
   - `DEMO.md` - Demo script

**Deliverables**:
- `docker-compose.yml` working
- CI/CD pipeline
- >80% test coverage
- Complete documentation

---

## 📋 Phase-by-Phase Plan

### Phase 1: Foundation (Week 1)

| Agent | Task | Deliverable |
|-------|------|-------------|
| Agent 1 | MCP Server with logging | MCP tools work, logs to DB |
| Agent 2 | Dashboard backend skeleton | API endpoints stubbed |
| Agent 3 | Dashboard frontend skeleton | React app with routing |
| Agent 4 | Dataset downloader | Can download GitHub repo |
| Agent 5 | Docker setup | `docker-compose up` works |

**Checkpoint**: All services start, basic connectivity works

---

### Phase 2: Core Features (Week 2)

| Agent | Task | Deliverable |
|-------|------|-------------|
| Agent 1 | Complete RAG + logging | Full query/indexing logging |
| Agent 2 | Dashboard API complete | All endpoints working |
| Agent 3 | Dashboard UI complete | 5 pages functional |
| Agent 4 | Process Epstein-Files | 1000+ docs indexed |
| Agent 5 | Tests + CI/CD | Tests passing, CI working |

**Checkpoint**: Dashboard shows real data, can monitor queries and jobs

---

### Phase 3: Polish (Week 3)

| Agent | Task | Deliverable |
|-------|------|-------------|
| Agent 1 | Performance optimization | <2s query latency |
| Agent 2 | Analytics + WebSocket | Real-time updates |
| Agent 3 | Charts + polish | Beautiful, responsive UI |
| Agent 4 | Error handling | Robust processing |
| Agent 5 | Documentation complete | All docs ready |

**Checkpoint**: Production-ready, demo-ready

---

## 🎯 Dashboard UI Specifications

### Page 1: Dashboard (Home)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏠 Dashboard    📊 Analytics    🔍 Queries    📁 Jobs    ⚙️ Settings        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │   📊 Total Queries  │  │   ⏱️ Avg Response   │  │   📁 Documents      │ │
│  │   12,456            │  │   1.2 seconds       │  │   1,234             │ │
│  │   ↑ 23% vs last week│  │   ↓ 0.3s vs last wk │  │   ↑ 56 today        │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────┐  ┌───────────────────────────┐ │
│  │   📈 Query Activity (Live)              │  │   🕐 Recent Queries       │ │
│  │                                         │  │                           │ │
│  │   [Line chart - queries/min]            │  │   • "flight logs" - 2s    │ │
│  │   Current: 45 queries/min               │  │   • "palm beach" - 5s     │ │
│  │                                         │  │   • "witnesses" - 1m      │ │
│  └─────────────────────────────────────────┘  └───────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   📁 Active Indexing Jobs                                            │   │
│  │                                                                      │   │
│  │   Epstein-Files Dataset    [████████████░░░░░░░░] 65%               │   │
│  │   650/1000 files    ETA: 5m 30s    Status: Processing               │   │
│  │   Current: flight_logs_vol2.pdf                                      │   │
│  │   [View Details] [Cancel]                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │   🏥 System Health                  │  │   🔥 Top Queries            │  │
│  │                                     │  │                             │  │
│  │   ✅ MCP Server: Running            │  │   1. flight logs (234)      │  │
│  │   ✅ Vector DB: Connected           │  │   2. palm beach (189)       │  │
│  │   ✅ LLM: Available                 │  │   3. witness names (156)    │  │
│  │   ⚠️  Disk: 85% full                │  │                             │  │
│  └─────────────────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Page 2: Analytics

- Query trends (line chart, 7d/30d/90d)
- Popular queries (bar chart)
- Response time distribution (histogram)
- Document type breakdown (pie chart)
- Hourly usage heatmap

### Page 3: Queries

- Searchable query history table
- Filter by date, client type, response time
- Click to view full query + response + sources
- Export to CSV

### Page 4: Jobs

- List of all indexing jobs
- Progress bars with %
- Status badges (pending/processing/completed/failed)
- Real-time log viewer
- Cancel/retry buttons

---

## 🔌 API Contract

### MCP Server (stdio/SSE)

```python
# Tools
index_documents(folder_path: str) -> str
query_documents(query: str, top_k: int = 5) -> str
search_similar(query: str, top_k: int = 5) -> List[dict]
get_document_summary(source: str) -> str
list_indexed_documents() -> List[str]
delete_document(source: str) -> str
reset_index() -> str
check_status() -> dict

# Resources
stats://queries -> Query statistics
stats://documents -> Document statistics
stats://jobs -> Job statistics
stats://system -> System health
```

### Dashboard Backend (REST + WebSocket)

```
GET  /api/dashboard/queries?limit=50
GET  /api/dashboard/queries/stats?time_range=24h
GET  /api/dashboard/queries/{id}

GET  /api/dashboard/jobs
GET  /api/dashboard/jobs/{id}
GET  /api/dashboard/jobs/{id}/progress
POST /api/dashboard/jobs/{id}/cancel

GET  /api/dashboard/health
GET  /api/dashboard/metrics
GET  /api/dashboard/analytics

WS   /ws/dashboard
```

---

## 🚀 Deployment

### Local Development

```bash
# Start all services
docker-compose up

# MCP Server: stdio (for Claude Desktop)
# Dashboard Backend: http://localhost:8001
# Dashboard Frontend: http://localhost:3000
# Database: postgres://localhost:5432
```

### Production

```bash
# Railway/Render deployment
# - MCP Server as background worker
# - Dashboard as web service
# - PostgreSQL as database
```

---

## 📊 Success Metrics

| Metric | Target | How to Verify |
|--------|--------|---------------|
| MCP Tools | 8 working | Test with Claude Desktop |
| Query Logging | 100% | Check database after each query |
| Dashboard Pages | 5 complete | Navigate all pages |
| Real-time Updates | <1s delay | Watch job progress |
| Dataset Indexed | 1000+ docs | Check document count |
| Test Coverage | >80% | Run test suite |

---

## 🎬 Demo Flow (3 minutes)

```
1. Open Dashboard at http://localhost:3000
   - Show key metrics
   - Show system health

2. Open Claude Desktop
   - Ask: "What are the flight logs?"
   - Show response with citations

3. Back to Dashboard
   - Show new query appeared in Recent Queries
   - Show Query Activity spike
   - Click query to see details

4. Start Dataset Import
   - Click "Import from GitHub"
   - Paste: https://github.com/yung-megafone/Epstein-Files
   - Show progress bar updating in real-time

5. Show Jobs Page
   - Detailed progress
   - Logs streaming
   - Files processed count

6. Show Analytics Page
   - Query trends
   - Popular queries
   - System metrics over time
```

---

**Ready to assign agents? Start with Agent 1 (MCP Server)!**
